import random
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DummyDataService:
    """
    RAG実装前のダミーデータ提供サービス
    
    ⚠️ このクラスはテスト用です
    RAG実装後は削除されます
    """
    
    def __init__(self):
        self._init_dummy_data()
    
    def _init_dummy_data(self):
        """ダミーデータの初期化"""
        
        # 【ダミー】法令・規制データ
        self.dummy_regulations = [
            {
                "category": "酒税法",
                "points": [
                    "酒類製造免許の必要性確認",
                    "酒税の課税要件と税率の確認", 
                    "製造場所・設備基準の適合性"
                ]
            },
            {
                "category": "食品衛生法",
                "points": [
                    "食品製造業許可の取得",
                    "HACCP対応システムの構築",
                    "表示ラベルの法的要件確認"
                ]
            },
            {
                "category": "景品表示法",
                "points": [
                    "不当表示防止のための表現チェック",
                    "健康効果を謳う際の根拠確認",
                    "価格表示の適正性確認"
                ]
            },
            {
                "category": "薬機法",
                "points": [
                    "健康食品の効能表示規制",
                    "医薬品的効能の表現禁止",
                    "広告規制への適合性"
                ]
            }
        ]
        
        # 【ダミー】相談先担当者データ
        self.dummy_consultants = [
            {
                "name": "田中 法務",
                "department": "法務部",
                "expertise": "酒税法・食品衛生法",
                "specialties": ["酒類関連法令", "製造免許", "税務"]
            },
            {
                "name": "佐藤 品質",
                "department": "品質保証部", 
                "expertise": "食品安全・HACCP",
                "specialties": ["品質管理", "食品安全", "製造基準"]
            },
            {
                "name": "山田 マーケ",
                "department": "マーケティング部",
                "expertise": "景品表示法・広告規制",
                "specialties": ["広告表現", "プロモーション", "ブランディング"]
            },
            {
                "name": "鈴木 開発",
                "department": "商品開発部",
                "expertise": "商品企画・技術開発", 
                "specialties": ["商品設計", "技術評価", "市場分析"]
            },
            {
                "name": "高橋 営業",
                "department": "営業部",
                "expertise": "販売戦略・流通",
                "specialties": ["販売チャネル", "価格戦略", "顧客対応"]
            }
        ]
        
        # 【ダミー】過去の相談事例
        self.dummy_cases = [
            {
                "keywords": ["新商品", "アルコール", "低アルコール"],
                "common_questions": [
                    "アルコール度数1%未満の場合の酒税法適用について",
                    "低アルコール商品の製造免許要件",
                    "ノンアルコール表示の法的基準"
                ]
            },
            {
                "keywords": ["健康", "機能性", "効果"],
                "common_questions": [
                    "機能性表示食品としての届出要件",
                    "健康効果を謳える表現の範囲",
                    "科学的根拠の提出基準"
                ]
            },
            {
                "keywords": ["海外", "輸出", "国際"],
                "common_questions": [
                    "輸出先国の規制要件確認",
                    "国際認証取得の必要性",
                    "海外向け表示ラベルの要件"
                ]
            }
        ]
    
    def analyze_consultation_content(self, text: str, files_content: List[str] = None) -> Dict[str, Any]:
        """
        相談内容を分析してダミーの論点・質問・相談先を生成
        
        Args:
            text: 相談内容テキスト
            files_content: ファイルから抽出されたテキストのリスト
            
        Returns:
            Dict: 分析結果（ダミーデータ）
        """
        try:
            # 全テキストを結合
            combined_text = text
            if files_content:
                combined_text += " " + " ".join(files_content)
            
            combined_text = combined_text.lower()
            
            # キーワードマッチングで関連する論点を特定
            relevant_regulations = []
            relevant_questions = []
            
            for regulation in self.dummy_regulations:
                category_keywords = {
                    "酒税法": ["酒", "アルコール", "製造", "免許", "税"],
                    "食品衛生法": ["食品", "安全", "衛生", "haccp", "製造"],
                    "景品表示法": ["広告", "表示", "マーケティング", "宣伝", "効果"],
                    "薬機法": ["健康", "効能", "機能性", "医薬", "効果"]
                }
                
                keywords = category_keywords.get(regulation["category"], [])
                if any(keyword in combined_text for keyword in keywords):
                    relevant_regulations.append(regulation)
            
            # 関連する過去事例から質問を生成
            for case in self.dummy_cases:
                if any(keyword in combined_text for keyword in case["keywords"]):
                    relevant_questions.extend(case["common_questions"])
            
            # デフォルトで少なくとも2つの規制分野を含める
            if len(relevant_regulations) < 2:
                remaining_regulations = [r for r in self.dummy_regulations if r not in relevant_regulations]
                relevant_regulations.extend(random.sample(remaining_regulations, min(2, len(remaining_regulations))))
            
            # 論点を生成
            questions = []
            for regulation in relevant_regulations[:3]:  # 最大3つの規制分野
                questions.extend(regulation["points"][:2])  # 各分野から2つの論点
            
            # 過去事例からの質問を追加
            if relevant_questions:
                questions.extend(random.sample(relevant_questions, min(2, len(relevant_questions))))
            
            # 重複を削除し、最大5つに制限
            questions = list(dict.fromkeys(questions))[:5]
            
            # 適切な相談先を選定
            consultants = self._select_consultants(relevant_regulations, combined_text)
            
            # 相談内容の要約を生成
            summary = self._generate_summary(text, relevant_regulations)
            
            logger.info(f"【ダミーデータ】分析完了: 論点{len(questions)}件, 相談先{len(consultants)}名")
            
            return {
                "summary": summary,
                "questions": questions,
                "consultants": consultants,
                "analysis_metadata": {
                    "confidence": round(random.uniform(0.75, 0.95), 2),
                    "generated_at": datetime.now().isoformat(),
                    "used_dummy_data": True,
                    "matched_regulations": [r["category"] for r in relevant_regulations]
                }
            }
            
        except Exception as e:
            logger.error(f"【ダミーデータ】分析エラー: {e}")
            return self._get_fallback_result()
    
    def _select_consultants(self, regulations: List[Dict], text: str) -> List[Dict[str, str]]:
        """適切な相談先を選定"""
        selected = []
        
        # 規制分野に基づく選定
        regulation_mapping = {
            "酒税法": ["田中 法務"],
            "食品衛生法": ["田中 法務", "佐藤 品質"],
            "景品表示法": ["山田 マーケ"],
            "薬機法": ["田中 法務", "山田 マーケ"]
        }
        
        for regulation in regulations:
            mapped_names = regulation_mapping.get(regulation["category"], [])
            for name in mapped_names:
                consultant = next((c for c in self.dummy_consultants if c["name"] == name), None)
                if consultant and consultant not in selected:
                    selected.append({
                        "name": consultant["name"],
                        "department": consultant["department"],
                        "expertise": consultant["expertise"]
                    })
        
        # 商品開発関連のキーワードがある場合
        if any(keyword in text.lower() for keyword in ["新商品", "開発", "企画", "設計"]):
            dev_consultant = next((c for c in self.dummy_consultants if c["name"] == "鈴木 開発"), None)
            if dev_consultant and dev_consultant not in selected:
                selected.append({
                    "name": dev_consultant["name"],
                    "department": dev_consultant["department"], 
                    "expertise": dev_consultant["expertise"]
                })
        
        # 最低2名、最大3名を確保
        if len(selected) < 2:
            remaining = [c for c in self.dummy_consultants if c not in selected]
            additional = random.sample(remaining, min(2 - len(selected), len(remaining)))
            selected.extend([{
                "name": c["name"],
                "department": c["department"],
                "expertise": c["expertise"]
            } for c in additional])
        
        return selected[:3]  # 最大3名
    
    def _generate_summary(self, text: str, regulations: List[Dict]) -> str:
        """相談内容の要約を生成"""
        regulation_names = [r["category"] for r in regulations]
        
        if len(regulation_names) == 1:
            reg_text = regulation_names[0]
        elif len(regulation_names) == 2:
            reg_text = f"{regulation_names[0]}と{regulation_names[1]}"
        else:
            reg_text = f"{', '.join(regulation_names[:-1])}、{regulation_names[-1]}"
        
        # テキストの長さに応じて要約スタイルを調整
        if len(text) > 200:
            summary = f"詳細な企画内容について、主に{reg_text}の観点から検討が必要な案件です。"
        else:
            summary = f"{reg_text}に関連する企画案について、法令適合性と実現可能性の確認が必要です。"
        
        return summary
    
    def _get_fallback_result(self) -> Dict[str, Any]:
        """エラー時のフォールバック結果"""
        return {
            "summary": "企画内容について、法令適合性の確認が必要な案件です。",
            "questions": [
                "関連法令の適用範囲確認",
                "必要な許認可の特定",
                "コンプライアンスリスクの評価"
            ],
            "consultants": [
                {
                    "name": "田中 法務",
                    "department": "法務部",
                    "expertise": "酒税法・食品衛生法"
                },
                {
                    "name": "佐藤 品質", 
                    "department": "品質保証部",
                    "expertise": "食品安全・HACCP"
                }
            ],
            "analysis_metadata": {
                "confidence": 0.7,
                "generated_at": datetime.now().isoformat(),
                "used_dummy_data": True,
                "fallback": True
            }
        }
    
    def get_dummy_data_info(self) -> Dict[str, Any]:
        """ダミーデータの情報を返す（デバッグ用）"""
        return {
            "service": "DummyDataService",
            "version": "1.0.0",
            "description": "RAG実装前のテストデータ提供サービス",
            "regulations_count": len(self.dummy_regulations),
            "consultants_count": len(self.dummy_consultants),
            "cases_count": len(self.dummy_cases),
            "warning": "このサービスはテスト用です。RAG実装後は削除されます。"
        }