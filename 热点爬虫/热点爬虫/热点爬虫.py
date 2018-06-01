from selenium import webdriver
import time
import threading
import pymysql

#浏览器配置
def OpenBrower(a=2):
    global driver_0
    global driver_1
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images":2}
    chrome_options.add_experimental_option("prefs",prefs)#不开启图片
    if a==0 or a==2 :#a==2的话浏览器0，1都打开，a==1只打开浏览器1
        driver_0= webdriver.Chrome(executable_path=r"C:\chromedriver.exe",chrome_options=chrome_options)#路径前面要加个r，表示不进行转义，相当于c#的@
        driver_0.set_page_load_timeout(10)#页面最长加载时间,超过会抛出异常
    if a==1 or a==2 :
        driver_1= webdriver.Chrome(executable_path=r"C:\chromedriver.exe",chrome_options=chrome_options)
        driver_1.set_page_load_timeout(10) 
    print("浏览器打开")

#加载屏蔽词
SensitiveWord=[]#敏感词
def LoadSWords():
    #加载屏蔽词
    Sensitive=open("敏感词.txt",'r')
    while True:
        sword=Sensitive.readline()[:-1]#-1去掉换行符
        SensitiveWord.append(sword)
        if sword=='':
            SensitiveWord.remove("")
            break
    Sensitive.close()
    print('加载屏蔽词')

#写入标题缓存
def WriteTitleCache(titles):
    #缓存标题的意义在于即使重启程序也不会写入重复的内容
    title_cache=open('title_cache','w')
    for x in titles:
        title_cache.write(x+'\n')
        #直接用writeline的话，文件空白，程序也是不正常运行，原因未知
    title_cache.close()
    print('写入标题缓存')
    
#加载标题缓存
def LoadTitleCache():
    title_cache=open('title_cache','r')
    while True:
        title=title_cache.readline()[:-1]
        hot_title_old.append(title)
        if title=='':
            hot_title_old.remove('')
            break
    title_cache.close()
    print('加载标题缓存') 

#关键词过滤
def Filter(p):#如果p标签中包含则返回false
    for x in SensitiveWord:
        if x in p:
            return False
    return True

#热点信息结构
class hotIF:
    title=''
    #content=''
    url=''
    #hot_len=0
    sql_user=''
    sql_password=''
    sql_ip=''
hotIF0=hotIF()#记录热点信息

#获取第一个链接
def GetFURL(URL):
    global driver_1
    use_time=time.clock()#记录开始时间
    driver_1.get(URL)
    #print("url1:",URL)
    FURL=driver_1.find_element_by_xpath(
        """//div[@class="c-gap-bottom-small"]
        |//h3[@class="t c-gap-bottom-small"]
        |//div[@class="c-row"]/a""")
    print(FURL.text)
    if FURL.get_attribute("href")==None:
        FURL=driver_1.find_element_by_xpath('//h3[@class="t"]/a')
        if '的最新相关信息'in FURL.text:
            FURL=driver_1.find_element_by_xpath('//div[@class="c-row"]/a')
    print("获取链接用时",int((time.clock()-use_time)),"秒")
    hotIF0.title=FURL.text
    hotIF0.url=FURL.get_attribute("href")

#获取热点内容
def GetContent():
    global driver_1
    use_time=time.clock()#记录开始时间
    furl=hotIF0.url
    try:#超时后会停止加载，不需要其它的。接住异常就行
        driver_1.get(furl)
    except Exception as e:
        print(e)
    print("获取内容用时",int((time.clock()-use_time)),"秒")
    title=driver_1.find_elements_by_xpath('//p')
    a=''
    for x in range(0,len(title)):
        if Filter(title[x].text):
            a=a+title[x].text
    #hotIF0.content=a
    sql="""insert into wp_posts
    (post_author,post_title,post_content,post_date,post_excerpt,to_ping,pinged,post_content_filtered)
    values ('2','%s','%s',now(),'','','','');
        """%(hotIF0.title,a)
    try:#在sql语句中有可能出现',"。导致MySQL不能找到正确的值的范围
        cur0.execute(sql)
    except :
        print("写入数据库错误")
        print(sql)
        con0.rollback()#事务回滚
        if "'" in a:
            print("热点内容与SQL语句冲突")
            a.replace("'","‘")
            sql="""insert into wp_posts
    (post_author,post_title,post_content,post_date,post_excerpt,to_ping,pinged,post_content_filtered)
    values ('2','%s','%s',now(),'','','','');
        """%(hotIF0.title,a)
        else : 
            print("放弃这个热点")
            sql=''
    con0.commit()

#获取热点标题
hot_title=[]#记录当前热点标题
hot_title_old=[]#记录获取过的热点标题
def GetHotTitle():
    global driver_0
    global hot_title_old
    driver_0.get("http://top.baidu.com/buzz?b=1&fr=tph_right")#数据来源
    title=driver_0.find_elements_by_xpath('//a[@class="list-title"]')
    title_len=len(title)
    print(title_len)
    hot_title_old+=hot_title
    hot_title.clear()#清空
    for x in range(0,title_len):
        hot_title.append(title[x].text)
    WriteTitleCache(hot_title)#缓存标题
    return title

#不知道怎么取名
def Sion():
    global con0
    global cur0
    con0=pymysql.connect(host=hotIF0.sql_ip,user=hotIF0.sql_user,password=hotIF0.sql_password,charset='utf8')
    cur0=con0.cursor()
    cur0.execute("USE wordpress")
    print("数据库连接")
    OpenBrower()   
    LoadSWords()#每次获取内容都加载一次，更新屏蔽词不用重启软件
    title=[]
    try:
        title=GetHotTitle()#获取标题
    except :
        driver_0.quit()#除非网络极差基本不可能发生，不过还是加一下
        OpenBrower(0)#只打开第0个浏览器
    val_hot_now=0
    for x in range(0,len(title)):
        if hot_title[x] not in hot_title_old:#如果是新的热点内容
            print('第',val_hot_now,'个')
            try:
                GetFURL(title[x].get_attribute("href"))#获取网页内容的第一个链接
                GetContent()#获取第一个链接的内容，并写入数据库
                val_hot_now+=1
            except Exception as e:
                print("出了点小问题，重启下浏览器",e)
                driver_1.quit()#虽然找不到是什么原因，不过重启浏览器还挺有效，就是耗时间
                OpenBrower(1)#只打开第1个浏览器
    print('获取了',val_hot_now,'个热点')
    driver_1.quit()#使用完退出，尽量不占用服务器资源
    driver_0.quit()
    cur0.close()
    con0.close()
 
#########################################################################
#一个小时来一次
if __name__ == "__main__":
    hotIF0.sql_ip=input('输入数据库地址  ：')
    hotIF0.sql_user=input('输入数据库用户名：')
    hotIF0.sql_password=input('输入数据库密码  ：')
    yn=input('是否加载缓存的标题？（Y）')#yes or no
    if yn=='Y' or yn =='y':
        LoadTitleCache()
    ################循环
    last_run_time=int(time.clock())#上次运行时间
    num_run=0#运行次数
    while True:#定时器有点问题暂时先用这个
        if int(time.clock())-last_run_time>3600 or num_run==0:#距离上次运行的时间大于一小时,或者是第一次运行
            print('\n\n\n第',num_run,'次运行')
            last_run_time=int(time.clock())
            Sion()
            num_run+=1
        if len(hot_title_old)>2048:#清理title内的前一半标题
            for x in range(0,1024):
                del hot_title_old[x]
        time.sleep(5)#每5秒检查一次，降低消耗



"""2018.6.1 0:33 zanllp
    屏蔽词的加载改为每次获取标题之前加载一次，添加屏蔽词生效后不需要重启
    加入写入和加载标题缓存，重启之后可以直接读取上一次获取的标题，避免对热点内容的重复获取
    requests在较差的网络下对网页的内容获取不全，而selenium 不会发生这种情况，暂时还是先使用selenium
   2018.6.2 2:33
    要运行程序需要 chrome 和chromedrive （放在c盘根目录）
    输入数据库的配置后抛出异常检查，检查输入的配置是否有误，敏感词.txt是否存在（没有新建一个，我懒得改代码了）
    在没有title_cache的时候不要加载标题的缓存，在每次获取热点标题后会生成
    生成的文章作者是wp用户数据库里id为2的用户
    其它的好像没什么了，除了开始外在运行过程中可能出现的异常都有try catch
    运行中大部分的异常也都是在重科这样的垃圾网络才会出现，在腾讯云上基本只有超时抛出的
"""
