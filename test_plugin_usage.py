#!/usr/bin/env python3
"""
快速验证 get_plugin_usage 功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/home/ubuntu/maimai/MaiBot')

def test_get_plugin_usage():
    """测试获取插件使用说明功能"""
    print("=" * 60)
    print("测试: 获取插件使用说明功能")
    print("=" * 60)

    try:
        from plugins.perception_plugin import perception_manager

        # 测试1: 获取music_plugin使用说明
        print("\n[测试1] 获取 music_plugin 使用说明")
        print("-" * 60)

        usage = perception_manager.get_plugin_usage("music_plugin")

        if usage and "error" not in usage:
            print(f"✅ 成功获取使用说明")
            print(f"插件名称: {usage['plugin_name']}")
            print(f"显示名称: {usage['display_name']}")
            print(f"版本: {usage['version']}")
            print(f"作者: {usage['author']}")
            print(f"描述: {usage['description']}")

            # 命令
            if usage['commands']:
                print(f"\n命令数量: {len(usage['commands'])}")
                for cmd in usage['commands']:
                    status = "✅" if cmd['enabled'] else "⛔"
                    print(f"  {status} {cmd['name']}: {cmd['description']}")
            else:
                print("命令: 无")

            # 工具
            if usage['tools']:
                print(f"\n工具数量: {len(usage['tools'])}")
                for tool in usage['tools']:
                    status = "✅" if tool['enabled'] else "⛔"
                    print(f"  {status} {tool['name']}: {tool['description']}")
            else:
                print("工具: 无")

            # 事件处理器
            if usage['event_handlers']:
                print(f"\n事件处理器数量: {len(usage['event_handlers'])}")
                for handler in usage['event_handlers']:
                    status = "✅" if handler['enabled'] else "⛔"
                    print(f"  {status} {handler['name']}: {handler['description']}")
            else:
                print("事件处理器: 无")

            # README
            if usage['readme']:
                readme_preview = usage['readme'][:200].replace('\n', ' ')
                print(f"\nREADME: 有 ({len(usage['readme'])} 字符)")
                print(f"预览: {readme_preview}...")
            else:
                print("\nREADME: 无")

            # Manifest
            if usage['manifest']:
                print(f"Manifest: 有")
            else:
                print("Manifest: 无")

        else:
            print(f"❌ 失败: {usage.get('error', '未知错误')}")

        # 测试2: 获取不存在的插件
        print("\n" + "=" * 60)
        print("[测试2] 获取不存在的插件")
        print("-" * 60)

        usage2 = perception_manager.get_plugin_usage("nonexistent_plugin")

        if usage2 and "error" in usage2:
            print(f"✅ 正确返回错误: {usage2['error']}")
        else:
            print("❌ 应该返回错误但没有")

        # 测试3: 获取perception_plugin自身
        print("\n" + "=" * 60)
        print("[测试3] 获取 perception_plugin 自身")
        print("-" * 60)

        usage3 = perception_manager.get_plugin_usage("perception_plugin")

        if usage3 and "error" not in usage3:
            print(f"✅ 成功获取使用说明")
            print(f"插件名称: {usage3['plugin_name']}")
            print(f"工具数量: {len(usage3['tools'])}")
            print(f"事件处理器数量: {len(usage3['event_handlers'])}")

            # 列出所有工具
            print("\n工具列表:")
            for tool in usage3['tools']:
                print(f"  - {tool['name']}: {tool['description']}")

        else:
            print(f"❌ 失败: {usage3.get('error', '未知错误')}")

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_plugin_usage()
