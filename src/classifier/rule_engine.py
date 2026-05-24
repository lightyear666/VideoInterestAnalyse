"""分类引擎 — 规则分类 + B站tag映射"""
import yaml, re, os
from typing import List
from ..models import VideoRecord
from ..console import Console

class RuleClassifier:
    """基于规则和平台标签的视频分类器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'categories.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)['categories']
        
        # Build tag → category map
        self.tag_to_category = {}
        for cat_name, cat_data in self.config.items():
            for tag in cat_data.get('bili_tags', []):
                self.tag_to_category[tag] = cat_name
        
        # Build keyword → category map (compile regex)
        self.keyword_rules = []
        for cat_name, cat_data in self.config.items():
            for kw in cat_data.get('keywords', []):
                self.keyword_rules.append((re.compile(kw, re.IGNORECASE), cat_name))
        
        Console.info(f"分类引擎就绪: {len(self.tag_to_category)} 个平台标签映射, {len(self.keyword_rules)} 条关键词规则")
    
    def classify(self, record: VideoRecord) -> VideoRecord:
        """对单条记录进行分类"""
        # Step 1: B站 tag直接映射 (最高优先级)
        if record.platform == 'bilibili' and record.tag:
            cat = self.tag_to_category.get(record.tag)
            if cat:
                record.category = cat
                record.confidence = 'high'
                return record
        
        # Step 2: 关键词匹配 (中优先级)
        title = (record.title or '') + (record.tag or '')
        best_match = None
        best_len = 0
        for pattern, cat in self.keyword_rules:
            match = pattern.search(title)
            if match:
                match_len = len(match.group())
                if match_len > best_len:  # 最长匹配优先
                    best_match = cat
                    best_len = match_len
        
        if best_match:
            record.category = best_match
            record.confidence = 'medium'
            return record
        
        # Step 3: 兜底 — 默认归类生活
        record.category = '生活'
        record.confidence = 'low'
        return record
    
    def classify_batch(self, records: List[VideoRecord]) -> List[VideoRecord]:
        """批量分类"""
        for i, r in enumerate(records):
            self.classify(r)
            if (i + 1) % 20 == 0:
                Console.progress(i + 1, len(records), "分类中...")
        Console.progress(len(records), len(records), "分类完成")
        print()
        return records


class VectorClassifier:
    """向量模型分类器 — 增强低置信度记录"""
    
    CATEGORY_ANCHORS = {
        "游戏": ["游戏实况攻略通关解说", "LOL英雄联盟王者荣耀DOTA2电竞比赛", "Steam单机独立3A大作", "我的世界Minecraft方舟"],
        "科技": ["编程教程Python Java C++开发", "电脑硬件装机显卡CPU评测", "人工智能机器学习ChatGPT", "黑客网络安全逆向工程"],
        "教育": ["考研考公四六级托福雅思", "数学物理化学课程学习", "PS PR AE教程学习", "计算机考试教学"],
        "音乐": ["音乐歌曲翻唱MV", "电音演奏钢琴吉他", "原创音乐人新歌", "演唱会Live现场"],
        "娱乐": ["综艺搞笑鬼畜搞笑视频", "Vlog日常挑战整活", "吐槽恶搞模仿短剧", "明星八卦娱乐圈"],
        "生活": ["美食探店旅游攻略", "健身运动减肥塑形", "时尚穿搭美妆", "家居手工DIY", "宠物猫狗萌宠日常"],
        "体育": ["足球篮球NBA比赛", "跑步游泳健身拳击", "体育赛事直播"],
        "新闻": ["新闻时事热点政策", "社会财经国际报道", "新闻联播今日关注"],
        "影视": ["电影解说剧集纪录片", "电视剧韩剧美剧", "影视剪辑混剪"],
        "动漫": ["新番动漫动画MAD", "AMV手书二次元", "COS番剧角色"],
        "知识": ["科普历史哲学经济", "商业读书人文社科", "知识分享读书"],
    }
    
    def __init__(self):
        self.model = None
        self.available = False
        self._centers = {}
    
    def try_load(self):
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            Console.info("加载向量模型 paraphrase-multilingual-MiniLM-L12-v2 ...")
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.np = np
            self.available = True
            Console.ok(f"模型加载完成 (设备: {self.model.device})")
            
            # 预计算类别中心向量
            Console.info("计算类别锚点向量...")
            for cat, anchors in self.CATEGORY_ANCHORS.items():
                embs = self.model.encode(anchors, show_progress_bar=False)
                self._centers[cat] = np.mean(embs, axis=0)
            Console.ok(f"已加载 {len(self._centers)} 个类别中心")
            return True
        except ImportError:
            Console.warn("sentence-transformers 未安装")
        except Exception as e:
            Console.warn(f"模型加载失败: {e}")
        return False
    
    def classify(self, record: VideoRecord) -> VideoRecord:
        """对单条记录分类"""
        if not self.available:
            return record
        
        title = (record.title or '') + ' ' + (record.tag or '')
        if len(title.strip()) < 2:
            return record
        
        try:
            emb = self.model.encode([title], show_progress_bar=False)[0]
            best_cat, best_score = None, -1
            
            for cat, center in self._centers.items():
                sim = float(self.np.dot(emb, center) / (self.np.linalg.norm(emb) * self.np.linalg.norm(center)))
                if sim > best_score:
                    best_score = sim
                    best_cat = cat
            
            if best_score > 0.3:  # 相似度阈值
                record.category = best_cat
                record.confidence = 'high' if best_score > 0.6 else 'medium'
        except:
            pass
        
        return record
    
    def classify_batch(self, records: list) -> list:
        """批量向量分类 — 对低置信度记录增强"""
        if not self.available:
            return records
        
        low_conf = [r for r in records if r.confidence == 'low']
        if not low_conf:
            Console.info("无低置信度记录需要增强")
            return records
        
        Console.info(f"向量增强 {len(low_conf)} 条低置信度记录...")
        
        titles = [(r.title or '') + ' ' + (r.tag or '') for r in low_conf]
        embs = self.model.encode(titles, show_progress_bar=True, batch_size=32)
        
        changed = 0
        for i, r in enumerate(low_conf):
            emb = embs[i]
            best_cat, best_score = None, -1
            for cat, center in self._centers.items():
                sim = float(self.np.dot(emb, center) / (self.np.linalg.norm(emb) * self.np.linalg.norm(center)))
                if sim > best_score:
                    best_score = sim
                    best_cat = cat
            
            if best_score > 0.3:
                old_cat = r.category
                r.category = best_cat
                r.confidence = 'high' if best_score > 0.6 else 'medium'
                if old_cat != best_cat:
                    changed += 1
        
        Console.ok(f"向量增强完成: {changed}/{len(low_conf)} 条记录重新分类")
        return records
