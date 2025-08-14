#!/usr/bin/env python3
"""MySQL接続テスト"""

import asyncio
from app.services.mysql_service import mysql_service

async def test_connection():
    print("MySQL接続テスト開始...")
    
    try:
        # 業界カテゴリ取得テスト
        print("業界カテゴリ取得テスト...")
        categories = await mysql_service.get_industry_categories()
        print(f"✅ 業界カテゴリ: {len(categories)}件取得")
        for cat in categories:
            print(f"  - {cat['category_code']}: {cat['category_name']}")
        
        # アルコール種別取得テスト
        print("\nアルコール種別取得テスト...")
        alcohol_types = await mysql_service.get_alcohol_types()
        print(f"✅ アルコール種別: {len(alcohol_types)}件取得")
        for alc in alcohol_types:
            print(f"  - {alc['type_code']}: {alc['type_name']}")
        
        # 検索テスト
        print("\n検索テスト...")
        results = await mysql_service.search_consultations(
            query=None,
            tenant_id="tenant_001",
            limit=10
        )
        print(f"✅ 検索結果: {len(results)}件")
        
        print("\n✅ 全てのテスト完了!")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())