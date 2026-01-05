# 代码风格和约定

## 通用规范

- 使用中文注释和文档字符串
- 模块顶部有中文文档字符串说明模块用途
- 类和方法使用中文文档字符串

## 类型提示

- 使用 `typing` 模块进行类型标注
- 示例: `Dict[str, GameState]`, `List[int]`, `Optional[str]`

## 类定义

- 使用 `@dataclass` 装饰器简化数据类
- 使用 `Enum` 定义枚举类型
- 使用属性装饰器 `@property`

## 异步编程

- 使用 `async/await` 进行异步操作
- 异步方法命名不需要特殊前缀

## 命名约定

- 类名: PascalCase (如 `GameState`, `PokerServer`)
- 方法名: snake_case (如 `handle_client`, `send_message`)
- 私有方法: 前缀下划线 (如 `_post_blinds`, `_calculate_side_pots`)
- 常量: 在 Enum 中定义

## 项目语言

- 代码注释: 中文
- 变量/函数名: 英文
- 用户界面文本: 中文
