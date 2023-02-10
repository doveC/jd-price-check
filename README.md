# jd-price-check

京东商品价格、优惠监控，并使用Server酱-PushDeer推送

## 使用说明

推送消息功能使用Server酱配合PushDeer直接推送到ios，详见[Server酱](https://sct.ftqq.com/)

新建 config.json，配置如下：（使用时请删除 // 及后面的文字）

````
{
    "items": [
        10045003937676, // 商品 ID
        10046635771777
    ],
    "proxy": "http://127.0.0.1:9999", // 代理地址，为空则不使用代理
    "push": {
        "sendKey": "ABCDEFG"  // PushDeer pushKey
    }
}
````

使用crontab定时执行该脚本即可

### 可选参数

```
usage: ./main.py [-l]

optional arguments:
  -l    show all item name and current price
```