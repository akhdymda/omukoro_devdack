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
            'content_spec': {# 中身仕様
                'keywords': ['品目', 'アルコール分', 'エキス分', '原料', '度数', '原材料'],
                'weight': 0.2
            },
            'container_spec': { # 容器仕様
                'keywords': ['缶', 'びん', '樽', 'PET', '紙パック', '容器', 'ボトル'],
                'weight': 0.2
            },
            'sales_method': { # 販売方法
                'keywords': ['通年', '期間限定', 'エリア限定', '店舗限定', 'ネット販売', '販売方法'],
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
        
        # 重要キーワードのチェック（中程度判定の保証）
        important_keywords = ['顧客', 'ターゲット', 'スケジュール', '計画', '品目', 'アルコール', '缶', 'びん']
        has_important_keyword = any(keyword in text for keyword in important_keywords)

        # 各カテゴリのスコアを計算
        category_scores = {}
        total_score = 0
        
        for category, rule in self.rules.items():
            score = self._calculate_category_score(text, rule['keywords'])
            category_scores[category] = score
            total_score += score * rule['weight']
        
        # 充実度スコアを1-5の範囲に正規化（より寛容な計算）
        if has_important_keyword:
        # 重要キーワードがある場合は最低3を保証
           base_score = max(0.6, total_score)  # 0.6 * 5 = 3
        else:
           base_score = max(0.4, total_score)  # 0.4 * 5 = 2
        # 充実度スコアを1-5の範囲に正規化
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
        if category_scores.get('market_analysis', 0) < 0.5:
            suggestions.append('市場分析の詳細化が必要です')
        if category_scores.get('content_spec', 0) < 0.5:
            suggestions.append('中味仕様（品目・アルコール分等）の記載が必要です')
        if category_scores.get('container_spec', 0) < 0.5:
            suggestions.append('容器仕様（缶・びん等）の明記が必要です')
        if category_scores.get('sales_method', 0) < 0.5:
            suggestions.append('販売方法（通年・限定等）の記載が必要です')
        if category_scores.get('implementation', 0) < 0.5:
            suggestions.append('実行計画の具体化が必要です')
        
        # デフォルトの提案
        if not suggestions:
            suggestions.append('全体的に充実した内容です')
        
        return suggestions[:3]  # 最大3件
