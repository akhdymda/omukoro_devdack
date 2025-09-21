import asyncio
import json
from app.services.simple_gremlin_service import SimpleGremlinService

async def debug_nodes_info():
    """ノード情報取得のデバッグ"""
    gremlin_service = SimpleGremlinService()
    
    try:
        # 接続
        connected = await gremlin_service.connect()
        print(f"接続状態: {connected}")
        
        if not connected:
            print("Gremlin接続に失敗しました")
            return
        
        # テストクエリ
        queries = [
            # クエリ1: エッジ情報を含む関連ノード取得
            """
            g.V().has('id', 'ビール').as('source')
            .bothE().as('edge')
            .otherV().as('target')
            .select('source', 'edge', 'target')
            .by(valueMap(true))
            """,
            
            # クエリ2: 基本的な関連ノード取得
            "g.V().has('id', 'ビール').both()",
            
            # クエリ3: エッジ経由で関連ノード取得
            "g.V().has('id', 'ビール').bothE().otherV()",
            
            # クエリ4: より詳細なエッジ情報取得
            """
            g.V().has('id', 'ビール')
            .bothE()
            .as('edge')
            .otherV()
            .as('target')
            .select('edge', 'target')
            .by(valueMap(true))
            """
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n=== クエリ {i} ===")
            print(f"クエリ: {query}")
            
            try:
                results = await gremlin_service.execute_query(query)
                print(f"結果数: {len(results)}")
                print(f"結果: {json.dumps(results, ensure_ascii=False, indent=2)}")
                
                # 各結果を解析
                for j, result in enumerate(results):
                    print(f"\n--- 結果 {j+1} ---")
                    print(f"型: {type(result)}")
                    print(f"内容: {result}")
                    
                    if isinstance(result, dict):
                        if 'source' in result and 'edge' in result and 'target' in result:
                            print("エッジ情報を含む結果")
                            print(f"ソース: {result.get('source', {})}")
                            print(f"エッジ: {result.get('edge', {})}")
                            print(f"ターゲット: {result.get('target', {})}")
                        elif 'id' in result and 'label' in result:
                            print("単純なノード結果")
                            print(f"ID: {result.get('id')}")
                            print(f"ラベル: {result.get('label')}")
                        else:
                            print("その他の辞書形式")
                            for key, value in result.items():
                                print(f"  {key}: {value}")
                    else:
                        print("辞書以外の形式")
                        
            except Exception as e:
                print(f"クエリ {i} でエラー: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await gremlin_service.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_nodes_info())
