#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import jieba
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SemanticSearch:
    def __init__(self):
        """初始化語義搜索"""
        # 食品類別詞典 - 可以擴展更多類別
        self.category_keywords = {
            '零食': ['零食', '小食', '點心', '薯片', '餅乾', '糖果', '巧克力', '爆米花'],
            '飲料': ['飲料', '果汁', '茶', '咖啡', '汽水', '奶茶', '礦泉水'],
            '主食': ['米飯', '麵條', '麵包', '饅頭', '粥', '湯麵', '炒飯'],
            '肉類': ['豬肉', '牛肉', '雞肉', '魚肉', '海鮮', '香腸', '火腿'],
            '蔬菜': ['蔬菜', '青菜', '白菜', '菠菜', '胡蘿蔔', '番茄', '洋蔥'],
            '水果': ['水果', '蘋果', '香蕉', '橘子', '草莓', '葡萄', '西瓜'],
            '健康': ['健康', '養生', '營養', '維生素', '蛋白質', '纖維', '低卡'],
            '美容': ['美容', '護膚', '保養', '抗衰老', '美白', '補水', '瘦身']
        }
    
    def expand_query(self, query: str) -> List[str]:
        """擴展查詢詞，增加相關詞彙"""
        expanded = [query]
        
        # 中文分詞
        words = list(jieba.cut(query))
        expanded.extend(words)
        
        # 根據類別擴展
        for category, keywords in self.category_keywords.items():
            if any(keyword in query for keyword in keywords):
                expanded.extend(keywords)
        
        # 去重並返回
        return list(set(expanded))
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """計算兩個文本的相似度（簡化版）"""
        try:
            # 簡單的Jaccard相似度
            words1 = set(jieba.cut(text1.lower()))
            words2 = set(jieba.cut(text2.lower()))
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            if len(union) == 0:
                return 0.0
            
            return len(intersection) / len(union)
            
        except Exception as e:
            logger.error(f"Calculate similarity failed: {e}")
            return 0.0
    
    def semantic_match(self, query: str, keywords: List[str], threshold: float = 0.1) -> List[Dict[str, Any]]:
        """語義匹配關鍵字"""
        matches = []
        
        # 擴展查詢詞
        expanded_query = self.expand_query(query)
        
        for keyword in keywords:
            # 直接匹配
            if query in keyword or keyword in query:
                matches.append({
                    'keyword': keyword,
                    'score': 1.0,
                    'match_type': 'exact'
                })
                continue
            
            # 語義相似度匹配
            max_score = 0.0
            for expanded in expanded_query:
                score = self.calculate_similarity(expanded, keyword)
                max_score = max(max_score, score)
            
            if max_score >= threshold:
                matches.append({
                    'keyword': keyword,
                    'score': max_score,
                    'match_type': 'semantic'
                })
        
        # 按分數排序
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches 