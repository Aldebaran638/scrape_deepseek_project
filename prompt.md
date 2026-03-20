- 项目根目录下test.html是一个示例html。我要求编写一个新模块。
新模块内容：
1.提供一个链接
2.抓取到链接中，test.html这样的元素(也就是class="product-list-wrap"的dev元素)
3.解析出该元素下,每一条li元素中的a链接和herf属性(比如<a href="/kr/ko/products/lumiwise-discoloration-corrector.html")
4.对于每一条链接,都调用模块sulwhasoo_scrapling_module来抓取链接中的关键信息.注意,不能直接进入a中的herf属性链接,而是要在链接前方加上https://www.sulwhasoo.com/才能正确抓取.
5.上述抓取每一条链接信息的循环,循环一次要停滞1.5s,防止过于频繁地访问

- 对于新增的产品列表抓取，新增一个逻辑：
新模块抓取的链接格式是：
https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=1
新增一个循环，存储一个临时值tmp
循环：
    如果https://www.sulwhasoo.com/kr/ko/products/skincare/skincare.html?page=${tmp},页面
    ,不存在li元素则退出循环
    反之如果存在,则进行原列表抓取逻辑(将页面下所有li元素中的a链接的产品信息抓取一遍)


我要求编写一个新模块,用来专门列表式抓取https://www.thesaemcosmetic.com/网站的内容。 
新模块抓取的链接格式是：
https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=1

抓取到链接中，test.html这样的元素(也就是class="wrapper"的元素) 
编写一个循环，存储一个临时值tmp 
循环：
    如果https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=${tmp},页面 
    ,在<ul class="item-list">下不存在li元素则退出循环 
    反之如果存在,则进行:
        解析出<ul class="item-list">下每一条li元素中的a链接和herf属性(比如<li> <a href="https://www.thesaemcosmetic.com/product/item.php?it_id=1773133732">)
        对于每一条链接,都调用模块thesaemcosmetic_scrapling_module来抓取链接中的关键信息.(上述抓取每一条链接信息的循环,循环一次要停滞1.5s,防止过于频繁地访问)
    
新模块传入的参数为https://www.thesaemcosmetic.com/product/index.php?&sort=&sca=&page=${a},a值为起始索引.假设a为3,那么上述循环tmp就从3开始




