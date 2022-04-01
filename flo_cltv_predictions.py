#VERİ SETİ HİKAYESİ
#Veri seti Flo’dan son alışverişlerini 2020 - 2021 yıllarında OmniChannel (hem online hem offline alışveriş yapan)
#olarak yapan müşterilerin geçmiş alışveriş davranışlarından elde edilen bilgilerden oluşmaktadır.


###########################  Görev 1: Veriyi Hazırlama  ##########################################
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from lifetimes.plotting import plot_period_transactions
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 500)
pd.set_option('display.float_format', lambda x: '%.4f' % x)
from sklearn.preprocessing import MinMaxScaler

#Adım1: flo_data_20K.csv verisini okuyunuz.
df_ = pd.read_csv("Projects/FLO_CLTV_Tahmini/flo_data_20k.csv")
df = df_.copy()
df.head()
#Adım2: Aykırı değerleri baskılamak için gerekli olan outlier_thresholds ve replace_with_thresholds fonksiyonlarını tanımlayınız.
#Not: cltv hesaplanırken frequency değerleri integer olması gerekmektedir.Bu nedenle alt ve üst limitlerini round() ile yuvarlayınız.

def outlier_thresholds(dataframe, variable):
    quartile1 = dataframe[variable].quantile(0.01)
    quartile3 = dataframe[variable].quantile(0.99)
    interquantile_range = quartile3 - quartile1
    up_limit = (quartile3 + 1.5 * interquantile_range).round()
    low_limit = (quartile1 - 1.5 * interquantile_range).round()
    return low_limit, up_limit


def replace_with_thresholds(dataframe, variable):
    low_limit, up_limit = (outlier_thresholds(dataframe, variable))
    # dataframe.loc[(dataframe[variable] < low_limit), variable] = low_limit # >>>> bu veri seti için aşağı outlier yok
    dataframe.loc[(dataframe[variable] > up_limit), variable] = up_limit


#Adım3: "order_num_total_ever_online", "order_num_total_ever_offline", "customer_value_total_ever_offline",
#            "customer_value_total_ever_online" değişkenlerinin aykırı değerleri varsa baskılayanız.
df.dtypes
df.describe().T
df.head()
df.isnull().sum()
columns = ["order_num_total_ever_online", "order_num_total_ever_offline", "customer_value_total_ever_offline", "customer_value_total_ever_online" ]
for col in columns:
    replace_with_thresholds(df, col)

#Adım4: Omnichannel müşterilerin hem online'dan hem de offline platformlardan alışveriş yaptığını ifade etmektedir.
# Her bir müşterinin toplam alışveriş sayısı ve harcaması için yeni değişkenler oluşturunuz.

df["Omnichannel_order_num_total"] = df["order_num_total_ever_online"] + df["order_num_total_ever_offline"]
df["Omnichannel_Value_Total"] = df["customer_value_total_ever_online"] + df["customer_value_total_ever_offline"]

df.describe().T

#Adım5: Değişken tiplerini inceleyiniz. Tarih ifade eden değişkenlerin tipini date'e çeviriniz.

df.dtypes
date_columns = df.columns[df.columns.str.contains("date")]
df[date_columns] = df[date_columns].apply(pd.to_datetime)

#############################  Görev 2: CLTV Veri Yapısının Oluşturulması  ###############################

#Adım1: Veri setindeki en son alışverişin yapıldığı tarihten 2 gün sonrasını analiz tarihi olarak alınız.

df.head()
df["last_order_date"].max()
today_date = dt.datetime(2021, 6, 1)
type(today_date)
#Adım2: customer_id, recency_cltv_weekly, T_weekly, frequency ve monetary_cltv_avg değerlerinin yer aldığı yeni bir cltv dataframe'i oluşturunuz.
#Monetary değeri satın alma başına ortalama değer olarak, recency ve tenure değerleri ise haftalık cinsten ifade edilecek.

cltv_df = pd.DataFrame()
cltv_df["customer_id"] = df["master_id"]
cltv_df["recency_cltv_weekly"] = ((df["last_order_date"]- df["first_order_date"]).astype('timedelta64[D]')) / 7
cltv_df["T_weekly"] = ((today_date - df["first_order_date"]).astype('timedelta64[D]'))/7
cltv_df["frequency"] = df["Omnichannel_order_num_total"]
cltv_df["monetary_cltv_avg"] = df["Omnichannel_Value_Total"] / df["Omnichannel_order_num_total"]

cltv_df.columns = ["customer_id", "recency", "T", "frequency", "monetary"]
cltv_df.head()


################  Görev 3: BG/NBD, Gamma-Gamma Modellerinin Kurulması ve CLTV’nin Hesaplanması #################
#Adım1: BG/NBD modelini fit ediniz.


bgf = BetaGeoFitter(penalizer_coef=0.001)
bgf.fit(cltv_df["frequency"],
            cltv_df["recency"],
            cltv_df["T"])




#3 ay içerisinde müşterilerden beklenen satın almaları tahmin ediniz ve
# exp_sales_3_month olarak cltv dataframe'ine ekleyiniz.

cltv_df["expected_purc_3_month"] = bgf.predict(12,
                                                   cltv_df['frequency'],
                                                   cltv_df['recency'],
                                                   cltv_df['T'])
#6 ay içerisinde müşterilerden beklenen satın almaları tahmin ediniz ve
# exp_sales_6_month olarak cltv dataframe'ine ekleyiniz.
cltv_df["expected_purc_6_month"] = bgf.predict(24,
                                                   cltv_df['frequency'],
                                                   cltv_df['recency'],
                                                   cltv_df['T'])
#Adım2: Gamma-Gamma modelini fit ediniz. Müşterilerin ortalama bırakacakları değeri tahminleyip
# exp_average_value olarak cltv dataframe'ine ekleyiniz.

ggf = GammaGammaFitter(penalizer_coef=0.01)
ggf.fit(cltv_df['frequency'], cltv_df['monetary'])
cltv_df["exp_average_value"] = ggf.conditional_expected_average_profit(cltv_df['frequency'],
                                                                                 cltv_df['monetary'])
cltv_df.head()

#Adım3: 6 aylık CLTV hesaplayınız ve cltv ismiyle dataframe'e ekleyiniz.

cltv_df["cltv"] = ggf.customer_lifetime_value (bgf,
                                   cltv_df['frequency'],
                                   cltv_df['recency'],
                                   cltv_df['T'],
                                   cltv_df['monetary'],
                                   time=6,  # 6 aylık
                                   freq="W",  # T'nin frekans bilgisi.
                                   discount_rate=0.01) #paranın gelecek değerini göz önüne almak için bugünkü değeri (enf. oranı gibi alınabilir)

###########################  Görev 4: CLTV Değerine Göre Segmentlerin Oluşturulması  ###################

#6 aylık CLTV'ye göre tüm müşterilerinizi 4 gruba (segmente) ayırınız ve grup isimlerini veri setine ekleyiniz.
# Cltv değeri en yüksek 20 kişiyi gözlemleyiniz.
cltv_df["segment"] = pd.qcut(cltv_df["cltv"], 4, labels=["D", "C", "B", "A"])
cltv_df.sort_values("cltv", ascending=False)[:20]

