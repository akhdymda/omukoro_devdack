import asyncio
import json
from app.services.simple_gremlin_service import SimpleGremlinService

async def debug_gremlin_query():
    """Gremlinクエリの結果をデバッグ"""
    gremlin_service = SimpleGremlinService()
    
    try:
        # 接続
        connected = await gremlin_service.connect()
        print(f"接続状態: {connected}")
        
        if not connected:
            print("Gremlin接続に失敗しました")
            return
        
        # より基本的なクエリをテスト
        query = "g.V().has('id', 'ビール').both()"
        
        print(f"実行するクエリ: {query}")
        
        # クエリ実行
        results = await gremlin_service.execute_query(query)
        print(f"結果数: {len(results)}")
        print(f"結果: {json.dumps(results, ensure_ascii=False, indent=2)}")
        
        # 別のクエリもテスト
        query2 = "g.V().has('id', 'ビール').bothE().otherV()"
        print(f"\n実行するクエリ2: {query2}")
        
        results2 = await gremlin_service.execute_query(query2)
        print(f"結果数2: {len(results2)}")
        print(f"結果2: {json.dumps(results2, ensure_ascii=False, indent=2)}")
        
        # 詳細なクエリ
        query3 = """
        g.V().has('id', 'ビール')
        .bothE()
        .as('edge')
        .otherV()
        .as('target')
        .select('edge', 'target')
        .by(valueMap(true))
        """
        
        print(f"\n実行するクエリ3: {query3}")
        
        results3 = await gremlin_service.execute_query(query3)
        print(f"結果数3: {len(results3)}")
        print(f"結果3: {json.dumps(results3, ensure_ascii=False, indent=2)}")
        
        # 各結果を解析
        for i, result in enumerate(results3):
            print(f"\n--- 結果 {i+1} ---")
            print(f"型: {type(result)}")
            print(f"内容: {result}")
            
            if isinstance(result, dict):
                edge_data = result.get('edge', {})
                target_data = result.get('target', {})
                print(f"エッジID: {edge_data.get('id', 'N/A')}")
                print(f"エッジラベル: {edge_data.get('label', 'N/A')}")
                print(f"ターゲットID: {target_data.get('id', 'N/A')}")
                print(f"ターゲットラベル: {target_data.get('label', 'N/A')}")
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await gremlin_service.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_gremlin_query())
