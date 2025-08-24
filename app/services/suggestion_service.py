from openai import AsyncOpenAI
import json
import hashlib
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.cosmos_service import CosmosService
from app.services.mysql_service import mysql_service
from app.services.advisor_service import AdvisorService
import logging
import pymysql

logger = logging.getLogger(__name__)

class SuggestionService:
    """相談内容から提案を生成するサービス"""
    
    def __init__(self):
        self.cosmos_service = CosmosService()
        
        # OpenAI クライアントを初期化
        api_key = settings.openai_api_key
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logger.warning("OpenAI API key is not set")
        
        # 新規追加: アドバイザーサービス
        self.advisor_service = AdvisorService(mysql_service)
        
        # 新規追加: データベースプール（専門用語取得用）
        # self.db_pool = mysql_service.pool  # 一時的にコメントアウト
    
    async def generate_suggestions(self, text: str, user_id: str = "1") -> Dict[str, Any]:
        """相談内容から提案を生成"""
        try:
            # 1. 法令検索
            regulations = self.cosmos_service.search_regulations(text, limit=5)
            
            # 2. タイトルの生成
            title = await self._generate_title(text)
            
            # 3. 業種・酒類カテゴリの選択
            industry_category_id, alcohol_type_id = await self._select_categories_with_openai(text)
            
            # 4. 主要論点の生成（リスト形式で取得）
            key_issues_list = await self._generate_key_issues(text, regulations)
            
            # 5. 提案質問の生成（既存のまま）
            suggested_questions = await self._generate_suggested_questions('\n'.join(key_issues_list))
            
            # 6. 次のアクションの生成
            action_items = await self._generate_action_items('\n'.join(key_issues_list))
            
            # 7. 専門用語の抽出・分析（新規追加）
            term_analysis = await self._extract_terms_from_key_issues(key_issues_list)
            
            # 7.5. 法令マッピング（新規追加）
            regulation_mapping = await self._map_regulations_to_key_issues(key_issues_list, regulations)
            
            # 8. 結果を統合
            consultation_id = await self._generate_consultation_id()
            
            result = {
                "consultation_id": consultation_id,
                "user_id": user_id,  # user_idを追加
                "title": title,
                "summary_title": f"{text[:50]}...",
                "initial_content": text,
                "industry_category_id": industry_category_id,
                "alcohol_type_id": alcohol_type_id,
                
                # 新規追加：個別論点
                "key_issue_1": key_issues_list[0] if len(key_issues_list) > 0 else '',
                "key_issue_2": key_issues_list[1] if len(key_issues_list) > 1 else '',
                "key_issue_3": key_issues_list[2] if len(key_issues_list) > 2 else '',
                
                # 新規追加：個別質問（ナンバリング追加）
                "suggested_question_1": f"1. {suggested_questions[0]}" if len(suggested_questions) > 0 else '',
                "suggested_question_2": f"2. {suggested_questions[1]}" if len(suggested_questions) > 1 else '',
                "suggested_question_3": f"3. {suggested_questions[2]}" if len(suggested_questions) > 2 else '',
                
                # 既存項目（プログラムベースで結合）
                "key_issues": '\n'.join(key_issues_list),
                "suggested_questions": suggested_questions,
                
                # 論点・質問ペア（修正後：番号除去、文頭に「論点：」「質問：」追加）
                "issue_question_pair_1": f"論点：{key_issues_list[0].replace('1. ', '') if key_issues_list[0].startswith('1. ') else key_issues_list[0]}\n質問：{suggested_questions[0]}" if len(key_issues_list) > 0 and len(suggested_questions) > 0 else '',
                "issue_question_pair_2": f"論点：{key_issues_list[1].replace('2. ', '') if key_issues_list[1].startswith('2. ') else key_issues_list[1]}\n質問：{suggested_questions[1]}" if len(key_issues_list) > 1 and len(suggested_questions) > 1 else '',
                "issue_question_pair_3": f"論点：{key_issues_list[2].replace('3. ', '') if key_issues_list[2].startswith('3. ') else key_issues_list[2]}\n質問：{suggested_questions[2]}" if len(key_issues_list) > 2 and len(suggested_questions) > 2 else '',
                
                # 新規追加：専門用語分析
                "term_name_1": term_analysis.get('term_name_1'),
                "term_name_2": term_analysis.get('term_name_2'),
                "term_name_3": term_analysis.get('term_name_3'),
                
                "term_definition_1": term_analysis.get('term_definition_1'),
                "term_definition_2": term_analysis.get('term_definition_2'),
                "term_definition_3": term_analysis.get('term_definition_3'),
                
                            "term_context_1": term_analysis.get('term_context_1'),
            "term_context_2": term_analysis.get('term_context_2'),
            "term_context_3": term_analysis.get('term_context_3'),
            
            # 新規追加：法令マッピング
            "relevant_regulation_1": regulation_mapping.get('relevant_regulation_1'),
            "relevant_regulation_2": regulation_mapping.get('relevant_regulation_2'),
            "relevant_regulation_3": regulation_mapping.get('relevant_regulation_3'),
            
            "relevant_reg_text_1": regulation_mapping.get('relevant_reg_text_1'),
            "relevant_reg_text_2": regulation_mapping.get('relevant_reg_text_2'),
            "relevant_reg_text_3": regulation_mapping.get('relevant_reg_text_3'),
            
            "action_items": action_items,
            "relevant_regulations": self._format_regulations_for_frontend(regulations)
            }
            
            # 8. 推奨相談先の取得（新規追加）
            recommended_advisor = None
            try:
                recommended_advisor = await self.advisor_service.get_recommended_advisor(
                    industry_category=result.get('industry_category_id'),
                    alcohol_type=result.get('alcohol_type_id')
                )
            except Exception as e:
                # アドバイザー取得エラーは推奨生成の失敗とはしない
                logger.error(f"推奨相談先取得エラー: {str(e)}")
            
            # 既存のレスポンスに推奨相談先を追加
            result['recommended_advisor'] = recommended_advisor
            # データベース保存用にIDも追加
            result['recommended_advisor_id'] = recommended_advisor.user_id if recommended_advisor else None
            
            # 7. データベースに保存（推奨相談先取得後に実行）
            try:
                await mysql_service.create_consultation(result)
                logger.info(f"相談データをデータベースに保存しました: {consultation_id}")
            except Exception as e:
                logger.error(f"データベース保存エラー: {e}")
                # 保存に失敗しても結果は返す
                pass
            
            logger.info(f"相談分析完了: ID={consultation_id}, 法令数={len(regulations)}")
            return result
            
        except Exception as e:
            logger.error(f"相談分析エラー: {e}")
            raise
    
    async def _generate_consultation_id(self) -> str:
        """相談IDを連番で生成"""
        try:
            # データベースから最新のconsultation_idを取得
            latest_id = await mysql_service.get_latest_consultation_id()
            
            if latest_id is None:
                # レコードが存在しない場合は1から開始
                return "1"
            
            # 最新のIDから次の番号を計算
            next_id = int(latest_id) + 1
            return str(next_id)
            
        except Exception as e:
            logger.error(f"consultation_id生成エラー: {e}")
            # エラー時はタイムスタンプベースのIDを生成
            import time
            return str(int(time.time()))
    
    def _format_regulations_for_frontend(self, regulations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """フロントエンド用に法令データをフォーマット"""
        formatted_regulations = []
        for reg in regulations:
            formatted_regulations.append({
                "chunk_id": reg["id"],
                "prefLabel": reg["prefLabel"],
                "section_label": reg["prefLabel"],
                "text": reg["text"],
                "score": reg["score"]
            })
        return formatted_regulations

    async def _select_categories_with_openai(self, text: str) -> tuple[str, str]:
        """OpenAI APIを使用して業種・酒類カテゴリを選択"""
        if not self.openai_client:
            # OpenAI API keyが設定されていない場合はデフォルト値を返す
            return "cat0001", "alc0001"
        
        try:
            # データベースから最新のカテゴリリストを取得
            industry_categories = await self._get_industry_categories()
            alcohol_types = await self._get_alcohol_types()
            
            if not industry_categories or not alcohol_types:
                logger.warning("カテゴリリストの取得に失敗しました")
                return "cat0001", "alc0001"
            
            # 業種カテゴリの選択
            industry_prompt = f"""
以下の相談内容に最も適切な業種カテゴリを選択してください。
選択肢は以下の通りです：

{self._format_industry_categories_for_prompt(industry_categories)}

相談内容: {text}

回答は選択肢のIDのみを返してください（例: cat0001）
"""
            
            industry_response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは業種分類の専門家です。相談内容に最も適切な業種カテゴリを選択してください。"},
                    {"role": "user", "content": industry_prompt}
                ],
                max_tokens=20,
                temperature=0.3
            )
            
            # OpenAIの応答からID部分のみを抽出
            response_content = industry_response.choices[0].message.content.strip()
            industry_category_id = response_content.split(':')[0].strip()
            
            # 酒類タイプの選択
            alcohol_prompt = f"""
以下の相談内容に最も適切な酒類タイプを選択してください。
選択肢は以下の通りです：

{self._format_alcohol_types_for_prompt(alcohol_types)}

相談内容: {text}

回答は選択肢のIDのみを返してください（例: alc0001）
"""
            
            alcohol_response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは酒類分類の専門家です。相談内容に最も適切な酒類タイプを選択してください。"},
                    {"role": "user", "content": alcohol_prompt}
                ],
                max_tokens=20,
                temperature=0.3
            )
            
            # OpenAIの応答からID部分のみを抽出
            response_content = alcohol_response.choices[0].message.content.strip()
            alcohol_type_id = response_content.split(':')[0].strip()
            
            # 取得したIDが有効かチェック
            if not self._is_valid_industry_category_id(industry_category_id, industry_categories):
                logger.warning(f"無効な業種カテゴリID: {industry_category_id}")
                industry_category_id = "cat0001"
            
            if not self._is_valid_alcohol_type_id(alcohol_type_id, alcohol_types):
                logger.warning(f"無効な酒類タイプID: {alcohol_type_id}")
                alcohol_type_id = "alc0001"
            
            return industry_category_id, alcohol_type_id
            
        except Exception as e:
            logger.error(f"カテゴリ選択エラー: {e}")
            return "cat0001", "alc0001"  # デフォルト値
    
    async def _get_industry_categories(self) -> List[Dict[str, Any]]:
        """業種カテゴリの一覧を取得"""
        try:
            if mysql_service.is_available():
                return await mysql_service.get_industry_categories()
            else:
                logger.warning("MySQLサービスが利用できません")
                return []
        except Exception as e:
            logger.error(f"業種カテゴリ取得エラー: {e}")
            return []
    
    async def _get_alcohol_types(self) -> List[Dict[str, Any]]:
        """酒類タイプの一覧を取得"""
        try:
            if mysql_service.is_available():
                return await mysql_service.get_alcohol_types()
            else:
                logger.warning("MySQLサービスが利用できません")
                return []
        except Exception as e:
            logger.error(f"酒類タイプ取得エラー: {e}")
            return []
    
    async def _generate_title(self, text: str) -> str:
        """入力内容から適切なタイトルを生成"""
        if not self.openai_client:
            # OpenAI API keyが設定されていない場合はデフォルト値を返す
            return "相談内容"
        
        try:
            prompt = f"""
以下の相談内容から、簡潔で分かりやすいタイトルを生成してください。

相談内容: {text}

要件:
- 20-30文字程度
- 相談の核心を表現
- 専門的すぎない表現
- ビジネスパーソンが理解しやすい内容

タイトルのみを出力してください。
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたはビジネス文書のタイトル作成の専門家です。相談内容から適切なタイトルを生成してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            title = response.choices[0].message.content.strip()
            # 引用符や改行を除去
            title = title.replace('"', '').replace("'", '').replace('\n', ' ').strip()
            
            if not title or title == "相談内容":
                return "相談内容"
            
            return title
            
        except Exception as e:
            logger.error(f"タイトル生成エラー: {e}")
            return "相談内容"  # デフォルト値
    
    def _format_industry_categories_for_prompt(self, categories: List[Dict[str, Any]]) -> str:
        """業種カテゴリをプロンプト用にフォーマット"""
        formatted = []
        for cat in categories:
            if cat.get('is_active', True):  # アクティブなカテゴリのみ
                formatted.append(f"- {cat['category_id']}: {cat['category_name']} ({cat['category_code']})")
        return '\n'.join(formatted)
    
    def _format_alcohol_types_for_prompt(self, types: List[Dict[str, Any]]) -> str:
        """酒類タイプをプロンプト用にフォーマット"""
        formatted = []
        for type_item in types:
            if type_item.get('is_active', True):  # アクティブなタイプのみ
                formatted.append(f"- {type_item['type_id']}: {type_item['type_name']} ({type_item['type_code']})")
        return '\n'.join(formatted)
    
    def _is_valid_industry_category_id(self, category_id: str, categories: List[Dict[str, Any]]) -> bool:
        """業種カテゴリIDが有効かチェック"""
        return any(cat['category_id'] == category_id for cat in categories)
    
    def _is_valid_alcohol_type_id(self, type_id: str, types: List[Dict[str, Any]]) -> bool:
        """酒類タイプIDが有効かチェック"""
        return any(type_item['type_id'] == type_id for type_item in types)
    
    async def _generate_key_issues(self, text: str, regulations: List[Dict[str, Any]]) -> List[str]:
        """主要論点を生成（3個の論点をリストで返却）"""
        if not self.openai_client:
            return [
                "酒税法の適用に関する主要な論点を確認する必要があります。",
                "酒税法の適用に関する主要な論点を確認する必要があります。",
                "酒税法の適用に関する主要な論点を確認する必要があります。"
            ]
        
        try:
            # 法令テキストを全文で取得（200文字制限を削除）
            regulations_text = "\n".join([
                f"- {reg['prefLabel']}: {reg['text']}"
                for reg in regulations
            ])
            
            prompt = f"""
以下の相談内容と関連法令の情報を基に、主要な論点を3個生成してください。

相談内容: {text}

関連法令:
{regulations_text}

主要な論点を3個生成してください。
各論点は250-300文字程度で、ひとつの文章は簡潔にしてください。
文章間は適切に改行を入れてください。
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは法律とビジネスの専門家です。相談内容を分析して、具体的で実用的な主要論点を提供してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,  # 250-300文字 × 3個 + 改行分で増加
                temperature=0.7
            )
            
            # 生成された論点を3個に分割
            content = response.choices[0].message.content
            # 改行で分割し、空行を除去
            issues = [issue.strip() for issue in content.split('\n') if issue.strip()]
            
            # 3個に制限し、不足分はデフォルト値で補完
            while len(issues) < 3:
                issues.append("酒税法の適用に関する主要な論点を確認する必要があります。")
            
            return issues[:3]  # 最大3個
            
        except Exception as e:
            logger.error(f"主要論点生成エラー: {e}")
            return [
                "酒税法の適用に関する主要な論点を確認する必要があります。",
                "酒税法の適用に関する主要な論点を確認する必要があります。",
                "酒税法の適用に関する主要な論点を確認する必要があります。"
            ]
    
    async def _generate_suggested_questions(self, key_issues: str) -> List[str]:
        """提案質問を生成"""
        if not self.openai_client:
            return [
                "酒税法の適用に関する主要な質問をする必要があります。",
                "酒税法の適用に関する主要な質問をする必要があります。",
                "酒税法の適用に関する主要な質問をする必要があります。"
            ]
        
        try:
            prompt = f"""
以下の主要論点を基に、専門家に質問する際の具体的な質問文を3個生成してください。

主要論点:
{key_issues}

各質問は以下の形式で出力してください：
- 具体的で実用的な内容
- 専門家が明確に回答できる形式
- ビジネスに直結する内容

各質問は100文字前後で、質問文のみを箇条書きで出力してください。
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは法令リスク判断の専門家支援AIです。入力として、ある企画に関する法律リスク論点（約300字）が与えられます。あなたの役割は、その内容から「専門家に確認すべき主要な事柄」に絞り込み、100字程度の日本語の質問文を1つ生成することです。制約条件: - 質問文は明確で、専門家が回答しやすい形にする - 不要な背景説明は含めない - 「〜について確認したい」などの問いかけ形式でまとめる"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            questions_text = response.choices[0].message.content
            questions = [q.strip() for q in questions_text.split('\n') if q.strip().startswith('-')]
            questions = [q[1:].strip() for q in questions if q[1:].strip()]
            
            if not questions:
                questions = [
                    "酒税法の適用に関する主要な質問をする必要があります。",
                    "酒税法の適用に関する主要な質問をする必要があります。",
                    "酒税法の適用に関する主要な質問をする必要があります。"
                ]
            
            return questions[:3]  # 3個に制限
            
        except Exception as e:
            logger.error(f"提案質問生成エラー: {e}")
            return [
                "酒税法の適用に関する主要な質問をする必要があります。",
                "酒税法の適用に関する主要な質問をする必要があります。",
                "酒税法の適用に関する主要な質問をする必要があります。"
            ]
    
    async def _generate_action_items(self, key_issues: str) -> str:
        """次のアクションを生成"""
        if not self.openai_client:
            return "酒税法の詳細調査を開始する\n専門家への相談を予約する\n必要な書類を準備する"
        
        try:
            prompt = f"""
以下の主要論点を基に、具体的な次のアクションを3-5個生成してください。

主要論点:
{key_issues}

各アクションは以下の形式で出力してください：
- 具体的で実行可能な内容
- 優先順位を考慮した内容
- ビジネスに直結する内容

各アクションは100-150文字程度で、アクション項目のみを箇条書きで出力してください。
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたはビジネスコンサルタントです。主要論点を基に、具体的で実行可能な次のアクションを生成してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            actions_text = response.choices[0].message.content
            actions = [a.strip() for a in actions_text.split('\n') if a.strip().startswith('-')]
            actions = [a[1:].strip() for a in actions if a[1:].strip()]
            
            if not actions:
                actions = [
                    "酒税法の詳細調査を開始する",
                    "専門家への相談を予約する",
                    "必要な書類を準備する"
                ]
            
            return '\n'.join(actions[:5])  # 最大5件
            
        except Exception as e:
            logger.error(f"アクション生成エラー: {e}")
            return "酒税法の詳細調査を開始する\n専門家への相談を予約する\n必要な書類を準備する"

    async def _extract_terms_from_key_issues(self, key_issues_list: List[str]) -> Dict[str, Any]:
        """主要論点から専門用語を抽出し、定義と文脈での意味合いを生成"""
        
        # データベースから専門用語一覧を取得
        terms = await self._get_term_definitions()
        
        result = {}
        
        for i, key_issue in enumerate(key_issues_list, 1):
            if not key_issue:
                # 空の場合はnullを設定
                result[f'term_name_{i}'] = None
                result[f'term_definition_{i}'] = None
                result[f'term_context_{i}'] = None
                continue
                
            # 専門用語の抽出（部分一致）
            matched_terms = []
            for term in terms:
                if term['term_name'] in key_issue:
                    matched_terms.append(term)
            
            if matched_terms:
                # 用語名、定義、文脈での意味合いを生成
                term_names = [term['term_name'] for term in matched_terms]
                term_definitions = [term['definition'] for term in matched_terms]
                
                # 区切り文字で結合（フロントエンドで区別しやすいように）
                result[f'term_name_{i}'] = ' | '.join(term_names)
                result[f'term_definition_{i}'] = ' | '.join(term_definitions)
                
                # 文脈での意味合いを生成
                context_meanings = []
                for term in matched_terms:
                    context = await self._generate_term_context(term['term_name'], key_issue)
                    context_meanings.append(context)
                
                result[f'term_context_{i}'] = ' | '.join(context_meanings)
            else:
                # ヒットしない場合はnullを設定
                result[f'term_name_{i}'] = None
                result[f'term_definition_{i}'] = None
                result[f'term_context_{i}'] = None
        
        return result

    async def _get_term_definitions(self) -> List[Dict[str, Any]]:
        """term_definitionテーブルから専門用語一覧を取得"""
        try:
            # mysql_serviceのget_connection()を使用して専門用語を取得
            async with mysql_service.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    query = "SELECT term_name, definition FROM term_definition ORDER BY term_id"
                    cursor.execute(query)
                    result = cursor.fetchall()
                    return result
                
        except Exception as e:
            logger.error(f"専門用語取得エラー: {e}")
            return []

    async def _generate_term_context(self, term_name: str, key_issue: str) -> str:
        """専門用語の文脈での意味合いを新入社員にもわかりやすく生成"""
        if not self.openai_client:
            return f"{term_name}について、この相談での意味を確認する必要があります。"
        
        try:
            prompt = f"""
以下の専門用語と相談内容から、新入社員にもわかりやすく、この相談での意味を100字以内で説明してください。

専門用語: {term_name}
相談内容: {key_issue}

説明のポイント:
- 新入社員でも理解できる簡単な言葉で
- この相談でなぜ重要かを具体的に
- 専門用語の意味を日常的な例えで説明
- 「つまり〜ということ」「簡単に言うと〜」などの表現を使う
- 100字以内で簡潔に

例:
- 「エキス分」→「つまり、お酒の濃さを表す数値で、この相談では計算方法を確認したいということ」
- 「発泡性酒類」→「簡単に言うと、泡が出るお酒のことで、この相談では製造許可の手続きを知りたいということ」
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは新入社員にもわかりやすく法令用語を説明する専門家です。難しい専門用語を日常的な言葉で分かりやすく説明してください。"},
                    {"role": "user", "content": prompt}
            ],
                max_tokens=200,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            return content if content else f"{term_name}について、この相談での意味を確認する必要があります。"
            
        except Exception as e:
            logger.error(f"文脈意味合い生成エラー: {e}")
            return f"{term_name}について、この相談での意味を確認する必要があります。"

    async def _find_matching_regulations(self, key_issue: str, regulations: List[Dict[str, Any]], threshold: float = 20.0) -> List[Dict[str, Any]]:
        """論点に関連する法令を複数選択（閾値以上のスコア）"""
        if not regulations:
            return []
        
        matching_regulations = []
        
        for regulation in regulations:
            score = await self._calculate_relevance_score(key_issue, regulation)
            if score >= threshold:
                matching_regulations.append({
                    'regulation': regulation,
                    'score': score
                })
        
        # スコア降順でソート
        matching_regulations.sort(key=lambda x: x['score'], reverse=True)
        
        return matching_regulations

    async def _calculate_relevance_score(self, key_issue: str, regulation: Dict[str, Any]) -> float:
        """論点と法令の関連性スコアを計算"""
        score = 0.0
        
        # 1. ベクトル検索スコア（既存のスコアを参考として使用）
        base_score = regulation.get('score', 0.0)
        score += base_score * 0.3  # 30%の重み
        
        # 2. キーワードマッチングスコア
        keyword_score = await self._calculate_keyword_match_score(key_issue, regulation)
        score += keyword_score * 0.7  # 70%の重み
        
        return score

    async def _calculate_keyword_match_score(self, key_issue: str, regulation: Dict[str, Any]) -> float:
        """キーワードマッチングによるスコア計算（term_definitionテーブルから動的取得）"""
        score = 0.0
        
        # 法令テキストとラベルからキーワードを抽出
        regulation_text = regulation.get('text', '')
        regulation_label = regulation.get('prefLabel', '')
        
        try:
            # term_definitionテーブルから動的にキーワードを取得
            keywords = await self._get_term_definitions()
            keyword_names = [term['term_name'] for term in keywords]
            
            # 論点と法令のキーワードマッチング
            for keyword in keyword_names:
                if keyword in key_issue:
                    # 論点にキーワードが含まれている場合
                    if keyword in regulation_text:
                        score += 10.0  # 法令テキストにも含まれている
                    if keyword in regulation_label:
                        score += 15.0  # 法令ラベルに含まれている場合はボーナス
                        
        except Exception as e:
            logger.error(f"キーワードマッチングスコア計算エラー: {e}")
            # エラー時は0点を返す
        
        return score

    def _format_regulation_info(self, regulations: List[Dict[str, Any]]) -> tuple[str, str]:
        """複数の法令情報を一つのフィールドにフォーマット"""
        if not regulations:
            return '', ''
        
        # prefLabelとtextを区切り文字で結合
        pref_labels = [reg['regulation']['prefLabel'] for reg in regulations]
        regulation_texts = [reg['regulation']['text'] for reg in regulations]
        
        # 区切り文字で結合（フロントエンドで区別しやすいように）
        formatted_labels = ' | '.join(pref_labels)
        formatted_texts = ' | '.join(regulation_texts)
        
        return formatted_labels, formatted_texts

    async def _map_regulations_to_key_issues(self, key_issues_list: List[str], regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """主要論点と関連法令を内容ベースでマッピング（複数選択対応）"""
        result = {}
        
        for i, key_issue in enumerate(key_issues_list, 1):
            if not key_issue:
                result[f'relevant_regulation_{i}'] = None
                result[f'relevant_reg_text_{i}'] = None
                continue
            
            # 閾値以上のスコアを持つ法令を複数選択
            matching_regulations = await self._find_matching_regulations(key_issue, regulations, threshold=20.0)
            
            if matching_regulations:
                # 複数の法令情報を一つのフィールドにフォーマット
                formatted_labels, formatted_texts = self._format_regulation_info(matching_regulations)
                result[f'relevant_regulation_{i}'] = formatted_labels
                result[f'relevant_reg_text_{i}'] = formatted_texts
            else:
                # 閾値未満の場合はnullを設定
                result[f'relevant_regulation_{i}'] = None
                result[f'relevant_reg_text_{i}'] = None
        
        return result

