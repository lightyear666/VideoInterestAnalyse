"""Cookie管理器 — 通过CDP从Edge提取Cookie"""
import subprocess, time, json, urllib.request, os, sys
import websocket

class CookieManager:
    """通过Edge CDP提取平台Cookie"""
    
    def __init__(self):
        self.edge_exe = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        self.user_data = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data')
        self.port = 9222
        self._proc = None
    
    def extract(self, platform: str, login_url: str = None) -> dict:
        """
        提取指定平台的Cookie
        
        Args:
            platform: 'bilibili' | 'douyin'
            login_url: 登录页面URL
        
        Returns:
            cookie字典 {name: value}
        """
        from .console import Console
        
        target_url = login_url or f'https://www.{platform}.com/'
        
        # 1. Kill existing Edge
        Console.info(f"关闭现有Edge进程...")
        subprocess.run(['taskkill','/F','/IM','msedge.exe'], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        # 2. Launch Edge with CDP
        Console.info(f"启动Edge (CDP模式)...")
        try:
            self._proc = subprocess.Popen([
                self.edge_exe,
                f'--remote-debugging-port={self.port}',
                '--remote-allow-origins=*',
                f'--user-data-dir={self.user_data}',
                '--no-first-run',
                target_url,
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            Console.err(f"Edge未安装在默认路径: {self.edge_exe}")
            return {}
        
        # 3. Wait for CDP
        time.sleep(3)
        for i in range(10):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/version', timeout=2)
                break
            except:
                time.sleep(1)
        
        # 4. Get cookies
        cookies = {}
        try:
            resp = urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json', timeout=3)
            targets = json.loads(resp.read())
            page = next((t for t in targets if t.get('type') == 'page'), None)
            
            if page:
                ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=5)
                ws.send(json.dumps({'id':1, 'method':'Network.getCookies', 
                                    'params':{'urls':[target_url]}}))
                result = json.loads(ws.recv())
                cookies = {c['name']: c['value'] for c in result['result']['cookies']}
                ws.close()
                
                Console.ok(f"提取到 {len(cookies)} 个Cookie")
        except Exception as e:
            Console.err(f"CDP连接失败: {e}")
        
        return cookies
    
    def re_extract(self, target_url: str = None) -> dict:
        """不重启Edge, 从已运行的CDP实例重新提取Cookie (先刷新页面再提取)"""
        from .console import Console
        
        url = target_url or 'https://www.douyin.com/'
        
        try:
            resp = urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json', timeout=3)
            targets = json.loads(resp.read())
            page = next((t for t in targets if t.get('type') == 'page'), None)
            
            if page:
                ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=5)
                
                # 先导航到目标页面刷新状态
                ws.send(json.dumps({'id':1, 'method':'Page.navigate', 'params':{'url': url}}))
                ws.recv()
                time.sleep(3)  # 等待页面加载+登录cookie生效
                
                # 然后提取Cookie
                ws.send(json.dumps({'id':2, 'method':'Network.getCookies', 
                                    'params':{'urls':[url]}}))
                result = json.loads(ws.recv())
                cookies = {c['name']: c['value'] for c in result['result']['cookies']}
                ws.close()
                
                has_session = 'sessionid' in cookies
                Console.ok(f"重新提取到 {len(cookies)} 个Cookie (sessionid={'Y' if has_session else 'N'})")
                return cookies
        except Exception as e:
            Console.err(f"重新提取失败: {e}")
        return {}
    
    def check_login(self, platform: str, cookies: dict) -> bool:
        """检查是否已登录 (抖音通过CDP浏览器上下文检测, 绕过反爬)"""
        from .console import Console
        
        if platform == 'bilibili':
            return self._check_bilibili(cookies)
        elif platform == 'douyin':
            return self._check_douyin_cdp()
        return False
    
    def _check_bilibili(self, cookies: dict) -> bool:
        from .console import Console
        cookie_str = '; '.join(f'{k}={v}' for k,v in cookies.items())
        try:
            req = urllib.request.Request('https://api.bilibili.com/x/web-interface/nav', headers={
                'User-Agent': 'Mozilla/5.0','Referer': 'https://www.bilibili.com/','Cookie': cookie_str,
            })
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            ok = resp.get('code') == 0 and resp.get('data', {}).get('isLogin')
            Console.info(f"B站登录: {'Y' if ok else 'N'} user={resp.get('data',{}).get('uname','?')}")
            return ok
        except Exception as e:
            Console.warn(f"B站检测失败: {e}")
        return False
    
    def _check_douyin_cdp(self) -> bool:
        """通过CDP检测抖音登录: 优先用sessionid判断 + API兜底"""
        from .console import Console
        try:
            resp = urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json', timeout=3)
            targets = json.loads(resp.read())
            page = next((t for t in targets if t.get('type') == 'page'), None)
            
            if page:
                ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=5)
                
                # 先用浏览器fetch检测 (绕过反爬)
                ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{
                    'expression': '''
                    (async () => {
                        try {
                            const resp = await fetch('https://www.douyin.com/aweme/v1/web/user/profile/self/', {
                                credentials: 'include',
                                headers: {'Referer': 'https://www.douyin.com/'}
                            });
                            const data = await resp.json();
                            return JSON.stringify({
                                ok: data.status_code === 0,
                                nickname: (data.user && data.user.nickname) || '',
                                code: data.status_code
                            });
                        } catch(e) {
                            return JSON.stringify({ok: false, error: e.message});
                        }
                    })()
                    ''',
                    'awaitPromise': True,
                    'returnByValue': True
                }}))
                
                for _ in range(15):
                    msg = json.loads(ws.recv())
                    if msg.get('id') == 1 and 'result' in msg:
                        raw = msg['result'].get('result', {}).get('value', '{}')
                        result = json.loads(raw) if isinstance(raw, str) else raw
                        
                        # 同时检查浏览器cookie中是否有sessionid
                        ws2_cmd = json.dumps({'id':2,'method':'Network.getCookies',
                            'params':{'urls':['https://www.douyin.com']}})
                        ws.send(ws2_cmd)
                        
                        cookies_raw = {}
                        for _ in range(15):
                            m2 = json.loads(ws.recv())
                            if m2.get('id') == 2:
                                cookies_raw = {c['name']:c['value'] for c in m2['result']['cookies']}
                                break
                        
                        has_session = 'sessionid' in cookies_raw
                        api_ok = result.get('ok', False)
                        nickname = result.get('nickname', '')
                        
                        # 任一条件满足即认为已登录
                        logged = has_session or api_ok
                        Console.info(f"抖音登录: {'Y' if logged else 'N'} sessionid={'Y' if has_session else 'N'} api={api_ok} nickname={nickname}")
                        ws.close()
                        return logged
                
                ws.close()
        except Exception as e:
            Console.warn(f"抖音CDP检测失败: {e}")
        return False
    
    def cleanup(self):
        """关闭Edge进程"""
        if self._proc:
            self._proc.terminate()
