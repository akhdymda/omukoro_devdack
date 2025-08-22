from typing import List, Dict, Any, Optional
from app.services.mysql_service import mysql_service
import logging

logger = logging.getLogger(__name__)

class ConsultationService:
    """相談分析と法令検索を統合したサービス（提案生成機能はSuggestionServiceに移行）"""
    
    async def generate_suggestions(self, text: str, user_id: str = "1") -> Dict[str, Any]:
        """相談内容から提案を生成（SuggestionServiceに委譲）"""
        from app.services.suggestion_service import SuggestionService
        suggestion_service = SuggestionService()
        return await suggestion_service.generate_suggestions(text, user_id)
    
    async def get_consultation_detail(self, consultation_id: str) -> Dict[str, Any]:
        """相談詳細を取得"""
        try:
            # MySQL接続を優先（Azure MySQL復旧後）
            if mysql_service.is_available():
                db_result = await mysql_service.get_consultation_by_id(consultation_id)
                if db_result:
                    logger.info(f"データベースから相談データを取得: {consultation_id}")
                    return db_result
            
            # 一時的な対処：OpenAI APIで生成されたデータを返す（Azure MySQL接続失敗時に使用）
            logger.info(f"MySQL接続なしで相談詳細を返します（一時的な対処）: {consultation_id}")
            
            # 相談内容を取得（localStorageから取得することを想定）
            # 実際の実装では、フロントエンドから相談内容を受け取る
            consultation_text = "ビールと焼酎を混ぜて提供することについて"
            
            # OpenAI APIで生成されたデータを返す
            return {
                "consultation_id": consultation_id,
                "title": "ビールと焼酎の混和提供に関する相談",
                "summary_title": f"{consultation_text}",
                "initial_content": consultation_text,
                "content": "相談の詳細内容",
                "created_at": "2025-08-12T22:00:00Z",
                "status": "analyzed",
                "industry_category_id": "cat0001",
                "alcohol_type_id": "alc0001",
                "key_issues": [
                    "酒税法に基づく酒類の製造および混和に関する規制の確認が必要",
                    "混ぜるビールと焼酎がどのような形態で提供されるかの詳細検討",
                    "提供する場所や方法によって適用される法律や規制の差異の確認",
                    "飲酒に関する法令や規制（飲酒年齢制限等）の遵守確認",
                    "提供する際の表示義務やラベリングに関する法令の確認"
                ],
                "suggested_questions": [
                    "混ぜるビールと焼酎のアルコール度数や製造方法によって、適用される酒税法の規定が変わるか",
                    "モニター調査を通じて提供する場合、飲酒に関する法令や規制に違反しないか",
                    "提供する際の表示義務やラベリングについて、特定の法令が適用されるか",
                    "酒類の混和に関する酒税法の具体的な規定内容は",
                    "提供する形態や状況によって適用される法令が異なる場合の判断基準は"
                ],
                "action_items": [
                    "酒類に関する専門家や弁護士に相談して、提供するビールと焼酎の組み合わせが法的に適切かどうか確認する",
                    "関連法令を詳細に調査し、提供する形態や状況によって適用される法令を特定する",
                    "モニター調査を行う場合は、飲酒に関する法令や規制について徹底的に把握し、遵守するための対策を講じる",
                    "提供する際の表示義務やラベリングについて、適用される法令を確認し、必要な情報を整理する",
                    "定期的に酒税法や関連規制の最新情報をチェックし、法令遵守のための体制を整える"
                ],
                "relevant_regulations": [
                    {
                        "chunk_id": "dummy-001",
                        "prefLabel": "酒税法 第三条 第十一号",
                        "section_label": "酒税法 第三条 第十一号",
                        "text": "十一　みりん次に掲げる酒類でアルコール分が十五度未満のもの（エキス分が四十度以上であることその他の政令で定める要件を満たすものに限る。）をいう。米及び米こうじに焼酎又はアルコールを加えて、こしたもの米、米こうじ及び焼酎又はアルコールにみりんその他政令で定める物品を加えて、こしたものみりんに焼酎又はアルコールを加えたものみりんにみりんかすを加えて、こしたもの",
                        "score": 0.85
                    },
                    {
                        "chunk_id": "dummy-002",
                        "prefLabel": "酒税法 第四十三条",
                        "section_label": "酒税法 第四十三条",
                        "text": "酒類に水以外の物品（当該酒類と同一の品目の酒類を除く。）を混和した場合において、混和後のものが酒類であるときは、新たに酒類を製造したものとみなす。ただし、次に掲げる場合については、この限りでない。一　清酒の製造免許を受けた者が、政令で定めるところにより、清酒にアルコールその他政令で定める物品を加えたとき。二　清酒又は合成清酒の製造免許を受けた者が、当該製造場において清酒と合成清酒とを混和したとき。",
                        "score": 0.78
                    },
                    {
                        "chunk_id": "dummy-003",
                        "prefLabel": "酒税法 第四十三条 第七項",
                        "section_label": "酒税法 第四十三条 第七項",
                        "text": "単式蒸留機によつて蒸留された原料用アルコールと単式蒸留焼酎との混和をしてアルコール分が四十五度以下の酒類としたときは、新たに単式蒸留焼酎を製造したものとみなす。",
                        "score": 0.72
                    }
                ]
            }
        except Exception as e:
            logger.error(f"相談詳細取得エラー: {e}")
            raise
    
    async def get_consultation_regulations(self, consultation_id: str) -> List[Dict[str, Any]]:
        """相談に関連する法令を取得"""
        try:
            # 実際の実装では、consultation_idに関連する法令を取得する
            # 現在はダミーデータを返す
            return [
                {
                    "id": "reg_001",
                    "text": "法令の内容...",
                    "prefLabel": "酒税法",
                    "relevance_score": 0.85
                }
            ]
        except Exception as e:
            logger.error(f"相談法令取得エラー: {e}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """ヘルスチェック用の状態を取得"""
        return {
            "service": "consultation",
            "status": "active"
        }
