import re
from typing import Dict, List

class RuleBasedAnalyzer:
    """ルールベース分析を行うクラス"""
    
    def __init__(self):
        # 分析ルールの定義
        self.rules = {
            'market_analysis': {
                'keywords': ['市場', 'ターゲット', '顧客', 'ニーズ', 'トレンド', '成長率'],
                'weight': 0.2
            },
            'competitor_analysis': {
                'keywords': ['競合', '競合他社', '差別化', '強み', '弱み', 'シェア'],
                'weight': 0.2
            },
            'risk_analysis': {
                'keywords': ['リスク', '課題', '問題', '懸念', '対策', '予防'],
                'weight': 0.2
            },
            'implementation': {
                'keywords': ['実行', '計画', 'スケジュール', 'マイルストーン', 'アクション', '実施'],
                'weight': 0.2
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
        
        for category, rule in self.rules.items():
            score = self._calculate_category_score(text, rule['keywords'])
            category_scores[category] = score
            total_score += score * rule['weight']
        
        # 充実度スコアを1-5の範囲に正規化
        completeness = max(1, min(5, int(round(total_score * 5))))
        
        # 改善提案を生成
        suggestions = self._generate_suggestions(category_scores)
        
        # 信頼度を計算
        confidence = min(1.0, 0.5 + (total_score * 0.5))
        
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
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 1.0
        
        # キーワードの出現回数も考慮
        for keyword in keywords:
            count = len(re.findall(keyword.lower(), text_lower))
            if count > 1:
                score += min(0.5, count * 0.1)
        
        return min(1.0, score / len(keywords))
    
    def _generate_suggestions(self, category_scores: Dict[str, float]) -> List[str]:
        """改善提案を生成"""
        suggestions = []
        
        # スコアが低いカテゴリについて提案を生成
        if category_scores.get('market_analysis', 0) < 0.5:
            suggestions.append('市場分析の詳細化が必要です')
        
        if category_scores.get('competitor_analysis', 0) < 0.5:
            suggestions.append('競合分析の強化が必要です')
        
        if category_scores.get('business_model', 0) < 0.5:
            suggestions.append('収益モデルの明確化が必要です')
        
        if category_scores.get('risk_analysis', 0) < 0.5:
            suggestions.append('リスク分析の追加が必要です')
        
        if category_scores.get('implementation', 0) < 0.5:
            suggestions.append('実行計画の具体化が必要です')
        
        # デフォルトの提案
        if not suggestions:
            suggestions.append('全体的に充実した内容です')
        
        return suggestions[:3]  # 最大3件
