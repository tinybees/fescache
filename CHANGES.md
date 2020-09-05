## fescache Changelog

###[1.0.0b1] - 2020-9-3

#### Added
- 增加同步异步install时的选择功能，需要指定是同步还是异步
- 重构异步redis客户端功能，更严谨现在直接是StrictRedis的子类,实现也更合理无数据不再抛出异常
- 重构异步redis客户端，去掉多余的日志打印，只保留出问题时的日志

#### Changed 
- 优化所有代码中没有类型标注的地方,都改为typing中的类型标注
- 拆分aclients库和eclients中的和redis相关的功能形成新的库,减少安装包的依赖
