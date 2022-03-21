import smtplib
from email.mime.text import MIMEText

import pandas as pd
import datetime
from pytz import timezone

from dateutil.relativedelta import relativedelta

from config import filter_config

from exchangelib import DELEGATE, IMPERSONATION, Account, Credentials, ServiceAccount, \
    EWSDateTime, EWSTimeZone, Configuration, Message, Mailbox, FileAttachment, HTMLBody
from email.mime.text import MIMEText
from email.header import Header

now = datetime.datetime.now()
today = datetime.datetime.now().date()
yesterday = today - datetime.timedelta(days=1)
current_num_of_week = (today + datetime.timedelta(days=1)).isocalendar()[1]

db_url = 'postgresql+psycopg2://artichoke:edt-1234@monitor.wifiprobe.edt.testritegroup.com/artichoke'
mail_server = '172.17.120.159'
mail_port = 25
mail_from = 'ASUS-monitor@edt.testritegroup.com'
to_mail = ['hi0006@testritegroup.com']
mail_subject = '{} 提袋率 & 人流 Daily Report'.format(today)

# E-mail settings
sender = 'hi0006@testritegroup.com'
recipients = [sender, 
              'cloude.chiu@testritegroup.com'
             ]
cc_recipients = []

taiwan2018_holiday = [
    datetime.date(2018, 1, 1),
    datetime.date(2018, 2, 15),
    datetime.date(2018, 2, 16),
    datetime.date(2018, 2, 19),
    datetime.date(2018, 2, 20),
    datetime.date(2018, 2, 28),
    datetime.date(2018, 4, 4),
    datetime.date(2018, 4, 5),
    datetime.date(2018, 4, 6),
    datetime.date(2018, 5, 1),
    datetime.date(2018, 6, 18),
    datetime.date(2018, 9, 3),
    datetime.date(2018, 9, 24),
    datetime.date(2018, 10, 10),
    datetime.date(2018, 11, 22),
    datetime.date(2018, 11, 23),
    datetime.date(2018, 12, 24),
    datetime.date(2018, 12, 25),
    datetime.date(2018, 12, 31),
]

taiwan2018_adjusted_work = [
    datetime.date(2018, 3, 31),
    datetime.date(2018, 12, 22),
]


def f(d):
    if type(d) is pd.Timestamp:
        d = d.date()

    if d in taiwan2018_holiday:
        return True

    if d in taiwan2018_adjusted_work:
        return False

    return d.weekday() >= 5



tw_timezone = timezone('Asia/Taipei')

week_number = 1
fetch_number_day = 60  # week_number * 7 if now.isoweekday() == 7 else now.isoweekday() + week_number * 7

start_date = today - datetime.timedelta(days=fetch_number_day)
end_date = today

data = []

### Target on released site
sql = '''SELECT site_id, sname, func[1], channel
    FROM public.site_info WHERE is_released=true;
'''

df = pd.read_sql(sql, db_url)
site_info_df = df[(df.channel.str.contains('TLW|CB|PETITE|HOLA|HOI')) & 
                  (~(df.site_id.str.contains('-area') | df.site_id.str.contains('-TEST')))]

for idx, site_info in site_info_df.iterrows():
    site_id = site_info.site_id[:4]
    # site_id = '1A07'

    ### 取得不重複會員交易數
    sql = '''SET SESSION TIME ZONE 'Asia/Taipei';
        SELECT sl_date as time, count_unique as tickets
        FROM epos_daily
          WHERE site_id = '{}' 
            AND sl_date BETWEEN '{}' AND '{}'
        '''.format(site_id, start_date, end_date)

    tickets_df = pd.read_sql(sql, db_url)
    tickets_df.time = tickets_df.time.apply(lambda t: t.astimezone(tw_timezone))

    sql='''
    SET SESSION TIME ZONE 'Asia/Taipei';
    SELECT date_trunc('day', time) as time, sum(count) as customers
    FROM people_count
    WHERE site_id= '{}' 
        AND time BETWEEN '{}' AND '{}'
        AND CAST(date_part('hour', time) AS INT) BETWEEN 10 AND 21
    GROUP BY date_trunc('day', time)
    '''.format(site_id, start_date, end_date)

    customer_df = pd.read_sql(sql, db_url)
    customer_df.time = customer_df.time.apply(lambda t: t.astimezone(tw_timezone))

    if customer_df.empty or tickets_df.empty:
        continue

    df = pd.merge(tickets_df, customer_df, on='time').sort_values('time')
    df['func'] = site_info.func
    df['sname'] = site_info.sname
    df['site_id'] = site_id
    df['number_of_week'] = df.time.apply(lambda t: (t.date() + datetime.timedelta(days=1)).isocalendar()[1])
    df['holiday'] = df.time.apply(f)
    df['rate'] = df.tickets / df.customers
    df['day'] = df.time.apply(lambda t: t.date())
    df['number_of_week'] = df.day.apply(lambda d: (d + datetime.timedelta(days=1)).isocalendar()[1])

    # print(site_id)
    data.append(df)

total_df = pd.concat(data).sort_values(['day','site_id'])

def send_tlw_outlook_mail(title, content):
    title = "{}".format(title)
    credentials = Credentials(username='hi0006@testritegroup.com', password='asdeed3000*')
    config = Configuration(server='outlook.office365.com/EWS/Exchange.asmx', credentials=credentials)
    account = Account(primary_smtp_address=sender, config=config, autodiscover=False, access_type=DELEGATE)
    mail = Message(
        account=account,
        subject=title,
        body=HTMLBody('<html><body>{}</body></html>'.format(content)),
        to_recipients=recipients,
        cc_recipients=cc_recipients)
    mail.send()
    return

def aggregate_ticket(fetch_start_day, period_days):
    fetch_end_day = fetch_start_day - datetime.timedelta(days=period_days)
    tmp_aggregate_df = total_df[(fetch_start_day - datetime.timedelta(days=period_days) <= total_df.day) 
                                & (total_df.day < fetch_start_day)]
    tmp_aggregate_ticket_df = tmp_aggregate_df.groupby(
        ['func', 'sname']).rate.mean().reset_index().pivot_table(index=['sname', 'func'])
    tmp_aggregate_ticket_df['sliding_window'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).rate.mean().round(2)
    tmp_aggregate_ticket_df['sliding_window_std'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).rate.std().round(2)
    tmp_aggregate_ticket_df['sliding_window_max'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).rate.max().round(2)
    tmp_aggregate_ticket_df['sliding_window_min'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).rate.min().round(2)
    
    tmp_aggregate_ticket_df['customers'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).customers.sum()
    tmp_aggregate_ticket_df['tickets'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).tickets.sum()

    if len(tmp_aggregate_ticket_df) > 0:
        tmp_aggregate_ticket_df['rate'] = tmp_aggregate_ticket_df.apply(lambda x : 
                                                                        round(x['tickets']/x['customers'],2)
                                                                        ,axis=1)
    
    # filter smaple days not enough
    tmp_aggregate_ticket_df['cnt'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).rate.count()
    tmp_aggregate_ticket_df = tmp_aggregate_ticket_df[tmp_aggregate_ticket_df['cnt'] == period_days]
    del tmp_aggregate_ticket_df['cnt']
    return tmp_aggregate_ticket_df

def diff_aggregate_ticket(fetch_start_day, fetch_compare_start_day, period_days):
    empty_str = 'NoData'
    tmp_view_1 = aggregate_ticket(fetch_start_day, period_days).reset_index()
    tmp_view_2 = aggregate_ticket(fetch_compare_start_day, period_days).reset_index()
        
    tmp_view_1['rate_compare'] = tmp_view_1['sname'].apply( 
        lambda x : tmp_view_2[tmp_view_2['sname'] == x]['rate'].iloc[0] 
        if len(tmp_view_2[tmp_view_2['sname'] == x]) > 0 else empty_str
    )
    tmp_view_1['customers_compare'] = tmp_view_1['sname'].apply( 
        lambda x : tmp_view_2[tmp_view_2['sname'] == x]['customers'].iloc[0] 
        if len(tmp_view_2[tmp_view_2['sname'] == x]) > 0 else empty_str
    )
    tmp_view_1['tickets_compare'] = tmp_view_1['sname'].apply( 
        lambda x : tmp_view_2[tmp_view_2['sname'] == x]['tickets'].iloc[0] 
        if len(tmp_view_2[tmp_view_2['sname'] == x]) > 0 else empty_str
    )
    
    tmp_view_1['rate_diff'] = tmp_view_1.apply( 
        lambda x : round( (x['rate']-x['rate_compare']) , 2)
        if x['rate_compare'] != empty_str else 0 ,axis=1
    )

    tmp_view_diff = tmp_view_1.pivot_table(index=['sname', 'func'])
    return tmp_view_diff

def diff_ticket_from_today(period_days, fetch_day=None, compare_fetch_day=None):
    if fetch_day == None:
        fetch_day = today
    if compare_fetch_day == None:
        compare_fetch_day = today - datetime.timedelta(days=period_days)
    tmp_view = diff_aggregate_ticket(fetch_day, compare_fetch_day, period_days)
    date_period_label = '{3}~{2} vs {1}~{0}'.format(fetch_day- datetime.timedelta(days=1),
                                                    (fetch_day- datetime.timedelta(days=period_days)),
                                                    compare_fetch_day- datetime.timedelta(days=1),
                                                    (compare_fetch_day- datetime.timedelta(days=period_days))
                                                   )
    return tmp_view, date_period_label


# 最後七天跟上週差異分佈
period_days = 7
tmp_df, tmp_week_diff_rate_label = diff_ticket_from_today(period_days)

# 月提袋率與上月相比差異
period_days = 30
tmp_month_diff, fetch_month_label = diff_ticket_from_today(period_days)

# 月提袋率與去年同期相比差異
period_days = 30
prev_year_day = today - relativedelta(years=1)
tmp_year_diff, fetch_year_label =  diff_ticket_from_today(period_days, compare_fetch_day=prev_year_day)

def aggregate_customers(fetch_start_day, period_days):
    fetch_end_day = fetch_start_day - datetime.timedelta(days=period_days)
    tmp_aggregate_df = total_df[(fetch_start_day - datetime.timedelta(days=period_days) <= total_df.day) 
                                & (total_df.day < fetch_start_day)]
    tmp_aggregate_customers_df = tmp_aggregate_df.groupby(
        ['func', 'sname']).customers.mean().reset_index().pivot_table(index=['sname', 'func'])
    tmp_aggregate_customers_df['sliding_window'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).customers.mean().round(2)
    tmp_aggregate_customers_df['sliding_window_std'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).customers.std().round(2)
    tmp_aggregate_customers_df['sliding_window_max'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).customers.max().round(2)
    tmp_aggregate_customers_df['sliding_window_min'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).customers.min().round(2)
    
    # filter smaple days not enough
    tmp_aggregate_customers_df['cnt'] = tmp_aggregate_df.groupby(
        ['sname', 'func']).customers.count()
    tmp_aggregate_customers_df = tmp_aggregate_customers_df[tmp_aggregate_customers_df['cnt'] == period_days]
    del tmp_aggregate_customers_df['cnt']
    
    return tmp_aggregate_customers_df

def diff_aggregate_customers(fetch_start_day, fetch_compare_start_day, period_days):
    empty_str = 'NoData'
    tmp_view_1 = aggregate_customers(fetch_start_day, period_days).reset_index()
    tmp_view_2 = aggregate_customers(fetch_compare_start_day, period_days).reset_index()
    
    tmp_view_1['customers_diff'] = tmp_view_1['sname'].apply(
        lambda x : tmp_view_2[tmp_view_2['sname'] == x]['sliding_window'].iloc[0] 
        if len(tmp_view_2[tmp_view_2['sname'].astype(str) == x]) > 0 else empty_str
    )
    tmp_view_1['customers_diff'] = tmp_view_1.apply( 
        lambda x : round( (x['sliding_window']-x['customers_diff'])/x['customers_diff'] , 2)
        if x['customers_diff'] != empty_str else 0 ,axis=1
    )

    tmp_view_diff = tmp_view_1.pivot_table(index=['sname', 'func'])
    return tmp_view_diff

def diff_customer_from_today(period_days, fetch_day=None, compare_fetch_day=None):
    if fetch_day == None:
        fetch_day = today
    if compare_fetch_day == None:
        compare_fetch_day = today - datetime.timedelta(days=period_days)
    tmp_view = diff_aggregate_customers(fetch_day, compare_fetch_day, period_days)
    del tmp_view['customers']
    date_period_label = '{3}~{2} vs {1}~{0}'.format(fetch_day- datetime.timedelta(days=1),
                                                    (fetch_day- datetime.timedelta(days=period_days)),
                                                    compare_fetch_day- datetime.timedelta(days=1),
                                                    (compare_fetch_day- datetime.timedelta(days=period_days))
                                                   )
    return tmp_view, date_period_label

# 最後七天與上週的差異>5%
period_days = 7
tmp_week_diff_customer, tmp_week_diff_customer_label = diff_customer_from_today(period_days)
tmp_week_diff_customer.pivot_table(index=['sname', 'func'])

# 月人流數與上月相比差異>5%
period_days = 30
tmp_month_diff_customer, tmp_month_diff_customer_label = diff_customer_from_today(period_days)
tmp_month_diff_customer.pivot_table(index=['sname', 'func'])

# 月人流數與去年同期相比差異>5%
period_days = 30
prev_year_day = today - relativedelta(years=1)
tmp_year_diff_customer, tmp_year_diff_customer_label = diff_customer_from_today(period_days, 
                                                                                compare_fetch_day=prev_year_day)
tmp_year_diff_customer.pivot_table(index=['sname','func'])

# 提袋率過低的門店 (分通路設門檻)
period_days = 7
filter_last_day = today - datetime.timedelta(days=period_days)
filter_lower_df = tmp_df.reset_index()
filter_lower_df['channel'] = filter_lower_df['sname'].apply(
    lambda x : site_info_df[site_info_df['sname'] == x]['channel'].iloc[0] 
    if len(site_info_df[site_info_df['sname'] == x]) > 0 else 'None')
filter_lower_df['lower_threshold'] = filter_lower_df['channel'].apply(
    lambda x : filter_config[x] if x in filter_config else 0 )

def rename_columns(columns, post_fix='', override={}):
    modify_columns = []
    for column in columns:
        if column == 'sliding_window':
            modify_columns.append('{}平均值'.format(post_fix))
        elif column == 'sliding_window_std':
            modify_columns.append('{}標準差'.format(post_fix))
        elif column == 'sliding_window_max':
            modify_columns.append('{}最大值'.format(post_fix))
        elif column == 'sliding_window_min':
            modify_columns.append('{}最小值'.format(post_fix))
        elif column == 'lower_threshold':
            modify_columns.append('門檻值')
        elif column == 'day':
            modify_columns.append('日期(星期)')
        elif column == 'rate_diff':
            modify_columns.append('提袋率差異')
        elif column == 'rate':
            if column in override:
                modify_columns.append(override[column])
            else:
                modify_columns.append('提袋率')
        elif column == 'customers_diff':
            modify_columns.append('人流差異')
        else:
            modify_columns.append(column)
    return modify_columns

def weekday_text(weekday_num):
    text = ''
    if weekday_num == 1:
        text = '星期一'
    elif weekday_num == 2:
        text = '星期二'
    elif weekday_num == 3:
        text = '星期三'
    elif weekday_num == 4:
        text = '星期四'
    elif weekday_num == 5:
        text = '星期五'
    elif weekday_num == 6:
        text = '星期六'
    elif weekday_num == 7:
        text = '星期日'
    else:
        text = weekday_num
    return text

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<style>
body {}
</style>
<meta charset="UTF-8">
<title>Title of the document</title>
</head>

<body>
{}
</body>

</html>
'''

def format_html_table(t, rename_columns_post_fix='',override={}):
    t.columns = rename_columns(t.columns.values, post_fix=rename_columns_post_fix, override=override)
    
    if len(t) > 0 :
        html = t.to_html()
    else:
        html = '<h3>No Data<h3>'
    return html

body = ''
body += '<h1>提袋率</h1>\n'


body += '<h2>過去7天提袋率爆表門店</h2>\n'
t = total_df[(today - datetime.timedelta(days=7) < total_df.day) & (1.0 <= total_df.rate)].loc[:,
    ['site_id', 'sname', 'func', 'rate', 'day', 'holiday', 'tickets', 'customers']]
t['day'] = t['day'].apply(lambda x : '{0}({1})'.format(x, weekday_text(x.isocalendar()[2])))
t['rate'] = t['rate'].apply(lambda x : '{0}%'.format(round(x*100,2)))
t = t.sort_values(['site_id','day'], ascending = [True,False]) 
body += t.to_html(index=False)

body += '<h2>過去7天提袋率與上週差異 5% 以上<br/>({})</h2>\n'.format(tmp_week_diff_rate_label)
t = tmp_df[0.05 <= abs(tmp_df['rate_diff'])]
t = t[['rate', 'rate_diff','sliding_window','sliding_window_std','sliding_window_max','sliding_window_min']]
t.columns = ['週提袋率', 'rate_diff','sliding_window','sliding_window_std',
             'sliding_window_max','sliding_window_min']
t = t.sort_values('rate_diff', ascending = False) 
t['rate_diff'] = t['rate_diff'].apply(lambda x : '{}%'.format(round(x*100,2)))
body += format_html_table(t, rename_columns_post_fix='過去7天')

body += '<h2>過去7天提袋率有出現超過 80% 並且標準差大於 0.1</h2>\n'
t = tmp_df[(0.8 <= tmp_df['sliding_window_max']) & (0.1 <= tmp_df.sliding_window_std)]
t = t[['rate','sliding_window','sliding_window_std','sliding_window_max','sliding_window_min']]
t.columns = ['週提袋率','sliding_window','sliding_window_std',
             'sliding_window_max','sliding_window_min']
t = t.sort_values('sliding_window_std', ascending = False) 
body += format_html_table(t, rename_columns_post_fix='過去7天')

body += '<h2>過去7天提袋率過低的門店 (小於門檻值)</h2>\n'
t = filter_lower_df[filter_lower_df.sliding_window_min <= filter_lower_df.lower_threshold]
t = t[['sname','func','channel','rate',
       'sliding_window','sliding_window_std','sliding_window_min','sliding_window_max']]
t.columns = ['sname','func','channel','週提袋率',
             'sliding_window','sliding_window_std','sliding_window_min','sliding_window_max']
t = t.sort_values('sliding_window_min', ascending = False)
t = t.set_index('sname','func')
hint_t = pd.DataFrame(filter_config, columns=filter_config.keys(), index=['門檻值'])
body += hint_t.to_html()
body += '<br/>'
body += format_html_table(t, rename_columns_post_fix='過去7天')

body += '<h2>月提袋率與上月相比差異>5% <br/>({})</h2>\n'.format(fetch_month_label)
t = tmp_month_diff[0.05 <= abs(tmp_month_diff['rate_diff'])]
t = t.sort_values('rate_diff', ascending = False) 
t = t[['rate', 'rate_diff', 'sliding_window', 'sliding_window_std','sliding_window_max',
       'sliding_window_min']]
t['rate_diff'] = t['rate_diff'].apply(lambda x : '{}%'.format(round(x*100,2)))
body += format_html_table(t, rename_columns_post_fix='過去30天', override={'rate':'月提袋率'})

body += '<h2>月提袋率與去年同期相比差異>5% <br/>({})</h2>\n'.format(fetch_year_label)
t = tmp_year_diff[0.05 <= abs(tmp_year_diff['rate_diff'])]
t = t[['rate', 'rate_diff', 'sliding_window', 'sliding_window_std','sliding_window_max',
       'sliding_window_min']]
t['rate_diff'] = t['rate_diff'].apply(lambda x : '{}%'.format(round(x*100,2)))
t = t.sort_values('rate_diff', ascending = False) 
body += format_html_table(t, override={'rate':'月提袋率'})

body += '<h1>人流數</h1>\n'

t = tmp_week_diff_customer[0.05 <= abs(tmp_week_diff_customer['customers_diff'])]
t = t.sort_values('customers_diff', ascending = False)
t = t[['customers_diff', 'sliding_window', 'sliding_window_std','sliding_window_max','sliding_window_min']]
t['customers_diff'] = t['customers_diff'].apply(lambda x : '{}%'.format(round(x*100,2)))
body += '<h2>過去7天與上週的差異>5% <br/>({})</h2>\n'.format(tmp_week_diff_customer_label)
body += format_html_table(t, rename_columns_post_fix='過去7天')

t = tmp_month_diff_customer[0.10 <= abs(tmp_month_diff_customer['customers_diff'])]
t = t.sort_values('customers_diff', ascending = False)
t = t[['customers_diff', 'sliding_window', 'sliding_window_std','sliding_window_max','sliding_window_min']]
t['customers_diff'] = t['customers_diff'].apply(lambda x : '{}%'.format(round(x*100,2)))
body += '<h2>月人流數與上月相比差異>10% <br/>({})</h2>\n'.format(tmp_month_diff_customer_label)
body += format_html_table(t, rename_columns_post_fix='過去30天')

t = tmp_year_diff_customer[0.10 <= abs(tmp_year_diff_customer['customers_diff'])]
t = t.sort_values('customers_diff', ascending = False)
t = t[['customers_diff', 'sliding_window', 'sliding_window_std','sliding_window_max','sliding_window_min']]
t['customers_diff'] = t['customers_diff'].apply(lambda x : '{}%'.format(round(x*100,2)))
body += '<h2>月人流數與去年同期相比差異>10% <br/>({})</h2>\n'.format(tmp_year_diff_customer_label)
body += format_html_table(t, rename_columns_post_fix='過去30天')


html = HTML_TEMPLATE.format("{font-family: calibri;}", body)

# smtp = smtplib.SMTP(mail_server, mail_port)
# msg = EmailMessage()

# msg = MIMEText(html, 'html')
# msg['From'] = mail_from
# msg['To'] = ','.join(to_mail)
# msg['Subject'] = mail_subject
# msg['Date'] = email.utils.localtime()

# msg.set_content(self.format(record))
# smtp.send_message(msg)
# smtp.quit()

send_tlw_outlook_mail(mail_subject,html)