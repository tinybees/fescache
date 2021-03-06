## fescache Changelog

###[1.0.0] - 2021-4-8

#### Added
- session中增加数据ID用于数据权限的存储.


###[1.0.0b6] - 2020-12-21

#### Changed
- 修复获取session如果个别字段不存在会报错的问题.


###[1.0.0b5] - 2020-11-7

#### Added
- 增加同步redis对fastapi的支持
- 增加服务停止自动清空连接池的功能对fastapi的支持

#### Changed
- 修复因为更改session类没有更改返回键导致的问题
- 修复因为多重继承造成的访问属性失败的问题

###[1.0.0b4] - 2020-9-26

#### Changed
- 修复同步异步获取session因为更改session类没有更改实例化参数导致的错误

###[1.0.0b3] - 2020-9-17

#### Changed
- 删除Session中不必要的ID,增加Session中缺少的ID
- 更改同步redis初始化APP的时机,改为调用即初始化

###[1.0.0b1] - 2020-9-3

#### Added
- 增加同步异步install时的选择功能，需要指定是同步还是异步
- 重构异步redis客户端功能，更严谨现在直接是StrictRedis的子类,实现也更合理无数据不再抛出异常
- 重构异步redis客户端，去掉多余的日志打印，只保留出问题时的日志
- 异步客户端增加连接超时参数，并且扩增其他关键字参数
- 重构同步redis客户端,功能和异步客户端类同,提取共同拥有的方法

#### Changed 
- 优化所有代码中没有类型标注的地方,都改为typing中的类型标注
- 拆分aclients库和eclients中的和redis相关的功能形成新的库,减少安装包的依赖
- 调试之前异步客户端有问题的日志造成的错觉上的影响,更改逻辑实现.
