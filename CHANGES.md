## fescache Changelog

###[1.0.0b1] - 2020-9-3

#### Added
- 增加同步异步install时的选择功能，需要指定是同步还是异步

#### Changed 
- 优化所有代码中没有类型标注的地方,都改为typing中的类型标注
- 拆分aclients库和eclients中的和redis相关的功能形成新的库,减少安装包的依赖
