"""
简单的测试文件 - 用于Git推送演示
"""

def test_addition():
    """测试加法"""
    assert 1 + 1 == 2
    print("✓ 加法测试通过")

def test_string():
    """测试字符串"""
    text = "Hello from Gitee!"
    assert "Hello" in text
    print(f"✓ 字符串测试通过: {text}")

def test_list():
    """测试列表"""
    fruits = ["苹果", "香蕉", "橙子"]
    assert len(fruits) == 3
    assert "香蕉" in fruits
    print(f"✓ 列表测试通过: {fruits}")

if __name__ == "__main__":
    print("运行测试...")
    test_addition()
    test_string()
    test_list()
    print("\n所有测试通过！✓")
