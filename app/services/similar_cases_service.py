import logging
from typing import List, Dict, Any, Optional
from app.services.mysql_service import mysql_service
from app.services.similarity_service import SimilarityService
from app.models.similar_cases import SimilarCaseResponse, SimilarCasesResponse

logger = logging.getLogger(__name__)

class SimilarCasesService:
    """類似相談案件取得専用サービス（MySQLサービスに直接接続）"""

    def __init__(self):
        self.similarity_service = SimilarityService()

    async def get_similar_cases(
        self,
        industry_category_id: Optional[str] = None,
        summary_title: Optional[str] = None,
        limit: int = 2
    ) -> SimilarCasesResponse:
        """
        類似相談案件を取得する
        
        Args:
            industry_category_id: 業種カテゴリID（指定時はその業種の相談のみ、未指定時は全件）
            summary_title: 新規生成された要約タイトル（類似度計算に使用）
            limit: 取得件数（デフォルト: 2、最大: 10）
            
        Returns:
            SimilarCasesResponse: 類似度の高い相談案件のリスト
        """
        try:
            # 1. 業種カテゴリでフィルタリング
            if industry_category_id:
                consultations = await mysql_service.search_consultations_for_similar_cases(
                    industry_categories=[industry_category_id],
                    limit=50,  # 類似度計算用に十分な件数を取得
                    offset=0
                )
                logger.info(f"業種カテゴリ {industry_category_id} で {len(consultations)} 件の相談を取得")
            else:
                consultations = await mysql_service.search_consultations_for_similar_cases(
                    limit=50,  # 類似度計算用に十分な件数を取得
                    offset=0
                )
                logger.info(f"全業種で {len(consultations)} 件の相談を取得")
            
            # consultation_idの最大値の1件を除外
            if len(consultations) > 1:
                # consultation_idでソートして最大値を特定
                consultations_sorted_by_id = sorted(consultations, key=lambda x: int(x['consultation_id']), reverse=True)
                max_consultation_id = consultations_sorted_by_id[0]['consultation_id']
                
                # 最大consultation_idの案件を除外
                consultations = [c for c in consultations if int(c['consultation_id']) != int(max_consultation_id)]
                
                logger.info(f"最大consultation_id {max_consultation_id} の1件を除外し、{len(consultations)} 件の相談案件で類似度計算を実行")
            
            if not consultations:
                logger.info("類似度計算対象の相談案件が見つかりませんでした")
                return SimilarCasesResponse(
                    similar_cases=[],
                    total_candidates=0,
                    message="類似度計算対象の相談案件が見つかりませんでした"
                )
            
            # 2. 要約タイトルが指定されている場合は類似度計算
            if summary_title:
                # 過去の要約データを準備
                past_summaries = []
                for consultation in consultations:
                    # summary_titleカラムが存在し、値がある場合のみ対象とする
                    if consultation.get('summary_title') and consultation['summary_title'].strip():
                        # データの型を適切に変換
                        consultation_id = str(consultation['consultation_id'])
                        summary_title_val = str(consultation['summary_title'])
                        title = str(consultation['title'])
                        created_at = consultation['created_at']
                        
                        past_summaries.append({
                            'id': consultation_id,
                            'summary': summary_title_val,
                            'title': title,
                            'created_at': created_at
                        })
                
                if not past_summaries:
                    logger.info("要約タイトルが設定されている相談案件が見つかりませんでした")
                    return SimilarCasesResponse(
                        similar_cases=[],
                        total_candidates=len(consultations),
                        message="要約タイトルが設定されている相談案件が見つかりませんでした"
                    )
                
                # 類似度計算を実行
                logger.info(f"要約タイトル '{summary_title}' と {len(past_summaries)} 件の過去要約で類似度計算を実行")
                similar_cases = await self.similarity_service.find_similar_cases(
                    new_summary=summary_title,
                    past_summaries=past_summaries,
                    limit=limit
                )
                
                logger.info(f"類似度計算完了: {len(similar_cases)} 件の類似案件を特定")
                
                # 類似度計算結果を新規レスポンスモデルに変換
                similar_case_responses = []
                for case in similar_cases:
                    # MySQLサービスから返されるデータをそのまま使用
                    consultation_data = next((c for c in consultations if str(c['consultation_id']) == case['id']), {})
                    
                    # データの型を適切に変換
                    created_at_str = str(case['created_at']) if case.get('created_at') else ''
                    
                    # key_issuesとaction_itemsをリストに変換
                    key_issues = consultation_data.get('key_issues', [])
                    if isinstance(key_issues, str) and key_issues:
                        try:
                            import json
                            key_issues = json.loads(key_issues)
                        except (json.JSONDecodeError, ValueError):
                            key_issues = []
                    elif not isinstance(key_issues, list):
                        key_issues = []
                    
                    action_items = consultation_data.get('action_items', [])
                    if isinstance(action_items, str) and action_items:
                        try:
                            import json
                            action_items = json.loads(action_items)
                        except (json.JSONDecodeError, ValueError):
                            action_items = []
                    elif not isinstance(action_items, list):
                        action_items = []
                    
                    similar_case_responses.append(SimilarCaseResponse(
                        consultation_id=case['id'],
                        title=case['title'],
                        summary_title=case['summary'],
                        created_at=created_at_str,
                        similarity_score=case.get('similarity_score'),
                        reason=case.get('reason'),
                        # 変換済みのデータを使用
                        key_issues=key_issues,
                        suggested_questions=consultation_data.get('suggested_questions', []),
                        action_items=action_items,
                        relevant_regulations=consultation_data.get('relevant_regulations', []),
                        detected_terms=consultation_data.get('detected_terms', []),
                        initial_content=consultation_data.get('initial_content', ''),
                        industry_category_id=consultation_data.get('industry_category_id', ''),
                        alcohol_type_id=consultation_data.get('alcohol_type_id', '')
                    ))
                
                return SimilarCasesResponse(
                    similar_cases=similar_case_responses,
                    total_candidates=len(past_summaries),
                    message=f"{len(similar_cases)} 件の類似案件を特定しました"
                )
            
            else:
                # 要約タイトルが指定されていない場合は、最新の相談案件を返却
                logger.info("要約タイトルが指定されていないため、最新の相談案件を返却")
                
                # 最新の相談案件を取得（limit件）
                recent_cases = consultations[:limit]
                
                # 最新の相談案件を新規レスポンスモデルに変換
                recent_case_responses = []
                for consultation in recent_cases:
                    # データの型を適切に変換
                    created_at_str = str(consultation['created_at']) if consultation.get('created_at') else ''
                    
                    # key_issuesとaction_itemsをリストに変換
                    key_issues = consultation.get('key_issues', [])
                    if isinstance(key_issues, str) and key_issues:
                        try:
                            import json
                            key_issues = json.loads(key_issues)
                        except (json.JSONDecodeError, ValueError):
                            key_issues = []
                    elif not isinstance(key_issues, list):
                        key_issues = []
                    
                    action_items = consultation.get('action_items', [])
                    if isinstance(action_items, str) and action_items:
                        try:
                            import json
                            action_items = json.loads(action_items)
                        except (json.JSONDecodeError, ValueError):
                            action_items = []
                    elif not isinstance(action_items, list):
                        action_items = []
                    
                    recent_case_responses.append(SimilarCaseResponse(
                        consultation_id=consultation['consultation_id'],
                        title=consultation['title'],
                        summary_title=consultation.get('summary_title', ''),
                        created_at=created_at_str,
                        similarity_score=None,  # 類似度計算未実行
                        reason='要約タイトルが指定されていないため、最新の相談案件を表示',
                        # 変換済みのデータを使用
                        key_issues=key_issues,
                        suggested_questions=consultation.get('suggested_questions', []),
                        action_items=action_items,
                        relevant_regulations=consultation.get('relevant_regulations', []),
                        detected_terms=consultation.get('detected_terms', []),
                        initial_content=consultation.get('initial_content', ''),
                        industry_category_id=consultation.get('industry_category_id', ''),
                        alcohol_type_id=consultation.get('alcohol_type_id', '')
                    ))
                
                return SimilarCasesResponse(
                    similar_cases=recent_case_responses,
                    total_candidates=len(consultations),
                    message=f"要約タイトルが指定されていないため、最新の {len(recent_cases)} 件の相談案件を表示"
                )
                
        except Exception as e:
            logger.error(f"類似相談案件取得エラー: {e}")
            raise

# サービスインスタンスを作成
similar_cases_service = SimilarCasesService()
