import re
from typing import Dict, List

class RuleBasedAnalyzer:
    """ルールベース分析を行うクラス"""
    
    def __init__(self):
        # 分析ルールの定義（4つの基本要素に基づく）
        self.rules = {
            'product_service': {
                'keywords': ['商品', 'サービス', '企画', '施策', 'プロダクト', '中味', '容器', '特徴', '仕様', 'アルコール', '素材'],
                'weight': 0.25
            },
            'target_customer': {
                'keywords': ['ターゲット', '顧客', '対象', 'ユーザー', 'ペルソナ', '年代', '購買動機', '価格帯'],
                'weight': 0.25
            },
            'schedule_timing': {
                'keywords': ['スケジュール', '時期', '期日', '日程', '月', '週', 'いつ', '開始', '終了', 'リリース', '目標'],
                'weight': 0.25
            },
            'purpose_goal': {
                'keywords': ['目的', '目標', 'KPI', 'ゴール', '狙い', '意図', '売上', 'シェア', '成長'],
                'weight': 0.25
            }
        }
    
    def analyze_text(self, text: str) -> Dict:
        """
        テキストを分析して充実度を評価
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            Dict: 分析結果
        """
        if not text or len(text.strip()) == 0:
            return {
                'completeness': 1,
                'suggestions': ['テキストが入力されていません'],
                'confidence': 1.0
            }
        
        # 各カテゴリのスコアを計算
        category_scores = {}
        total_score = 0
        covered_categories = 0
        
        for category, rule in self.rules.items():
            score = self._calculate_category_score(text, rule['keywords'])
            category_scores[category] = score
            total_score += score * rule['weight']
            if score > 0.3:  # カテゴリがカバーされているとみなす閾値
                covered_categories += 1
        
        # 充実度スコアを1-5の範囲に正規化
        # 4つのカテゴリのうち、カバーされている数に基づいて基本スコアを決定
        if covered_categories >= 4:
            # 全4カテゴリがカバーされている場合：レベル5
            base_score = max(0.8, total_score)
        elif covered_categories >= 3:
            # 3カテゴリがカバーされている場合：レベル4
            base_score = max(0.6, total_score)
        elif covered_categories >= 2:
            # 2カテゴリがカバーされている場合：レベル3
            base_score = max(0.4, total_score)
        else:
            # 1カテゴリ以下の場合：レベル1-2
            base_score = max(0.2, total_score)
        
        completeness = max(1, min(5, int(round(base_score * 5))))
        
        # 改善提案を生成
        suggestions = self._generate_suggestions(category_scores)
        
        # 信頼度を計算
        confidence = min(1.0, 0.7 + (total_score * 0.3))
        
        return {
            'completeness': completeness,
            'suggestions': suggestions,
            'confidence': confidence,
            'category_scores': category_scores
        }
    
    def _calculate_category_score(self, text: str, keywords: List[str]) -> float:
        """カテゴリごとのスコアを計算"""
        score = 0.0
        text_lower = text.lower()
        matched_keywords = 0
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched_keywords += 1
                score += 1.0
        
        # キーワードの出現回数も考慮
        for keyword in keywords:
            count = len(re.findall(keyword.lower(), text_lower))
            if count > 1:
                score += min(0.5, count * 0.1)

        # より寛容なスコア計算：1つでもマッチすれば基本点を与える
        if matched_keywords > 0:
        # マッチしたキーワード数に基づいてスコア調整
            base_score = min(1.0, 0.3 + (matched_keywords / len(keywords)) * 0.7)
        # 追加スコアも考慮
            additional_score = min(0.3, (score - matched_keywords) * 0.3)
            return min(1.0, base_score + additional_score)
        else:
            return 0.0
    
    def _generate_suggestions(self, category_scores: Dict[str, float]) -> List[str]:
        """改善提案を生成"""
        suggestions = []
        
        # スコアが低いカテゴリについて提案を生成
        if category_scores.get('product_service', 0) < 0.5:
            suggestions.append('商品・サービス内容の詳細化が必要です')
        
        if category_scores.get('target_customer', 0) < 0.5:
            suggestions.append('ターゲット顧客の具体化が必要です')
        
        if category_scores.get('schedule_timing', 0) < 0.5:
            suggestions.append('スケジュール・時期の明確化が必要です')
        
        if category_scores.get('purpose_goal', 0) < 0.5:
            suggestions.append('目的・目標の明確化が必要です')
        
        # デフォルトの提案
        if not suggestions:
            suggestions.append('全体的に充実した内容です')
        
        return suggestions[:3]  # 最大3件
