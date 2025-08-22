from openai import AsyncOpenAI
import json
import hashlib
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.cosmos_service import CosmosService
from app.services.mysql_service import mysql_service
import logging

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
    
    async def generate_suggestions(self, text: str, user_id: str = "1") -> Dict[str, Any]:
        """相談内容から提案を生成"""
        try:
            # 1. 法令検索
            regulations = self.cosmos_service.search_regulations(text, limit=5)
            
            # 2. タイトルの生成
            title = await self._generate_title(text)
            
            # 3. 業種・酒類カテゴリの選択
            industry_category_id, alcohol_type_id = await self._select_categories_with_openai(text)
            
            # 4. 主要論点の生成
            key_issues = await self._generate_key_issues(text, regulations)
            
            # 5. 提案質問の生成
            suggested_questions = await self._generate_suggested_questions(key_issues)
            
            # 6. 次のアクションの生成
            action_items = await self._generate_action_items(key_issues)
            
            # 7. 結果を統合
            consultation_id = self._generate_consultation_id(text)
            
            result = {
                "consultation_id": consultation_id,
                "user_id": user_id,  # user_idを追加
                "title": title,
                "summary_title": f"{text[:50]}...",
                "initial_content": text,
                "industry_category_id": industry_category_id,
                "alcohol_type_id": alcohol_type_id,
                "key_issues": key_issues,
                "suggested_questions": suggested_questions,
                "action_items": action_items,
                "relevant_regulations": self._format_regulations_for_frontend(regulations)
            }
            
            # 7. データベースに保存
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
    
    def _generate_consultation_id(self, text: str) -> str:
        """相談IDを生成"""
        # テキストのハッシュからIDを生成
        hash_object = hashlib.md5(text.encode())
        return f"consultation_{hash_object.hexdigest()[:8]}"
    
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
    
    async def _generate_key_issues(self, text: str, regulations: List[Dict[str, Any]]) -> str:
        """主要論点を生成"""
        if not self.openai_client:
            return "酒税法の適用に関する主要な論点を確認する必要があります。"
        
        try:
            regulations_text = "\n".join([
                f"- {reg['prefLabel']}: {reg['text'][:200]}..."
                for reg in regulations
            ])
            
            prompt = f"""
以下の相談内容と関連法令の情報を基に、主要な論点を3-5個生成してください。

相談内容: {text}

関連法令:
{regulations_text}

主要な論点を3-5個生成してください。
各論点は100-150文字程度で、具体的で実用的な内容にしてください。
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは法律とビジネスの専門家です。相談内容を分析して、具体的で実用的な主要論点を提供してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"主要論点生成エラー: {e}")
            return "酒税法の適用に関する主要な論点を確認する必要があります。"
    
    async def _generate_suggested_questions(self, key_issues: str) -> List[str]:
        """提案質問を生成"""
        if not self.openai_client:
            return [
                "酒税法の基本的な要件は何ですか？",
                "許可申請の手続きはどのようなものですか？",
                "更新手続きの期限はいつですか？"
            ]
        
        try:
            prompt = f"""
以下の主要論点を基に、専門家に質問する際の具体的な質問文を3-5個生成してください。

主要論点:
{key_issues}

各質問は以下の形式で出力してください：
- 具体的で実用的な内容
- 専門家が明確に回答できる形式
- ビジネスに直結する内容

各質問は100-150文字程度で、質問文のみを箇条書きで出力してください。
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは法律相談の専門家です。主要論点を基に、専門家への具体的な質問文を生成してください。"},
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
                    "酒税法の基本的な要件は何ですか？",
                    "許可申請の手続きはどのようなものですか？",
                    "更新手続きの期限はいつですか？"
                ]
            
            return questions[:5]  # 最大5件
            
        except Exception as e:
            logger.error(f"提案質問生成エラー: {e}")
            return [
                "酒税法の基本的な要件は何ですか？",
                "許可申請の手続きはどのようなものですか？",
                "更新手続きの期限はいつですか？"
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

