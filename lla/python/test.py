# 1. 定义装饰器
def my_logger(func):
    # 这里的 func 就是下面被装饰的 say_hello
    print(f"[系统] 正在初始化装饰器，目标函数是: {func.__name__}")
    
    # 定义包装函数（壳）
    def wrapper():
        print(">>> 开始执行... (这是装饰器添加的代码)")
        
        # 真正执行原函数
        func()  
        
        print("<<< 执行结束 (这是装饰器添加的代码)")
    
    # 返回包装好的新函数
    return wrapper

# 2. 使用装饰器
# 这一步相当于执行了: say_hello = my_logger(say_hello)
@my_logger
def say_hello():
    print("   Hello! 我是原函数里的逻辑。")

# 3. 主程序调用
if __name__ == "__main__":
    print("--- 准备调用函数 ---")
    
    # 表面上调用的是 say_hello，实际上调用的是 wrapper
    say_hello()
    
    print("--- 调用完毕 ---")