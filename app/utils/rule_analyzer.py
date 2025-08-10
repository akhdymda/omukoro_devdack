import re
from typing import Dict, List, Tuple
from app.models.analysis import RuleAnalysisResult

class RuleBasedAnalyzer:
    """
    ルールベースによるテキスト分析クラス
    """
    
    def __init__(self):
        # 各カテゴリのキーワードパターンを定義
        self.keywords = {
            'product': {
                'patterns': [r'商品', r'サービス', r'製品', r'プロダクト', r'システム', r'アプリ'],
                'name': '商品・サービス内容'
            },
            'target': {
                'patterns': [r'対象', r'ターゲット', r'顧客', r'ユーザー', r'利用者', r'お客様'],
                'name': '対象顧客・ターゲット'
            },
            'budget': {
                'patterns': [r'予算', r'コスト', r'費用', r'価格', r'料金', r'投資'],
                'name': '予算・コスト情報'
            },
            'timeline': {
                'patterns': [r'期間', r'スケジュール', r'時期', r'予定', r'納期', r'リリース'],
                'name': 'スケジュール・時期'
            },
            'purpose': {
                'patterns': [r'目的', r'目標', r'ゴール', r'狙い', r'効果', r'成果'],
                'name': '目的・目標'
            },
            'market': {
                'patterns': [r'市場', r'業界', r'競合', r'マーケット', r'需要'],
                'name': '市場・競合分析'
            }
        }
        
        # 最低文字数の閾値
        self.min_length_basic = 30    # 基本情報
        self.min_length_detail = 100  # 詳細情報
    
    def analyze_text(self, text: str) -> RuleAnalysisResult:
        """
        テキストをルールベースで分析する
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            RuleAnalysisResult: 分析結果
        """
        found_categories = []
        missing_categories = []
        
        # 各カテゴリのキーワードをチェック
        for category, info in self.keywords.items():
            if self._has_keyword(text, info['patterns']):
                found_categories.append(category)
            else:
                missing_categories.append(category)
        
        # スコア計算（0-2の3段階）
        score = self._calculate_score(text, len(found_categories))
        
        # 不足している要素をユーザー向けのメッセージに変換
        missing_elements = [
            self.keywords[cat]['name'] 
            for cat in missing_categories[:5]  # 最大5つまで表示
        ]
        
        # 文字数が不足している場合は追加
        if len(text) < self.min_length_basic:
            missing_elements.append('より詳細な説明')
        
        return RuleAnalysisResult(
            found_categories=found_categories,
            missing_categories=missing_categories,
            score=score,
            missing_elements=missing_elements
        )
    
    def _has_keyword(self, text: str, patterns: List[str]) -> bool:
        """
        テキスト内にキーワードパターンが含まれているかチェック
        
        Args:
            text: チェック対象のテキスト
            patterns: 検索パターンのリスト
            
        Returns:
            bool: パターンが見つかった場合True
        """
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _calculate_score(self, text: str, found_count: int) -> int:
        """
        スコアを計算する（0-2の3段階）
        
        Args:
            text: 分析対象のテキスト
            found_count: 見つかったカテゴリ数
            
        Returns:
            int: スコア（0-2）
        """
        text_length = len(text)
        
        # 文字数が極端に少ない場合は0
        if text_length < self.min_length_basic:
            return 0
        
        # カテゴリ数と文字数を組み合わせて判定
        if found_count >= 4 and text_length >= self.min_length_detail:
            return 2  # 詳細
        elif found_count >= 2 and text_length >= self.min_length_basic:
            return 1  # 中程度
        else:
            return 0  # 不足
    
    def get_improvement_suggestions(self, analysis_result: RuleAnalysisResult) -> List[str]:
        """
        改善提案を生成する
        
        Args:
            analysis_result: 分析結果
            
        Returns:
            List[str]: 改善提案のリスト
        """
        suggestions = []
        
        # 不足しているカテゴリに基づいて具体的な提案を生成
        for category in analysis_result.missing_categories[:3]:  # 上位3つ
            if category == 'product':
                suggestions.append('どのような商品・サービスなのか具体的に記載してください')
            elif category == 'target':
                suggestions.append('ターゲットとなる顧客層を明確にしてください')
            elif category == 'budget':
                suggestions.append('予算の規模や制約条件を記載してください')
            elif category == 'timeline':
                suggestions.append('スケジュールや期限を明確にしてください')
            elif category == 'purpose':
                suggestions.append('何を目的として実施するのかを明確にしてください')
            elif category == 'market':
                suggestions.append('対象市場や競合の状況を記載してください')
        
        return suggestions 