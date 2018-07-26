import requests
from flask import Flask, render_template
import pandas as pd
import re
from datetime import datetime
from wordcloud import WordCloud
import base64
from io import BytesIO

app = Flask(__name__)
app.debug = True

main_url = 'http://api.duma.gov.ru/api/'
my_token = '0fb77544c3c20cd24261b2302562091b44644913'
my_app_token = 'app3831cc79355d162d0de8b34e68ec427c12f4cb27'

prl = 'contprl'
gd = 'contgd'
sf = 'contsf'

def get_data(mainurl, mytoken, myapptoken):

    deputats_wet = requests.get(mainurl + mytoken +
                                '/deputies.json?app_token=' +
                                myapptoken).json()
    deputats = []
    for e in deputats_wet:
        ee = dict((k, v) for k, v in e.items() if k != 'factions' and k != 'id')
        if 'factions' in e and len(e['factions']) > 0:
            fa = e['factions'][-1]['name']
            fa_id = e['factions'][-1]['id']
        else:
            fa = 'Депутаты, не входящие во фракции'
            fa_id = 99111552

        ee['curr_last_faction'] = fa
        ee['curr_last_faction_id'] = fa_id
        ee['ind'] = e['id']
        deputats.append(ee)
    df = pd.DataFrame(deputats)

    return df


df  = get_data(main_url, my_token, my_app_token)


def get_team(df, team):

    names = {'GD' : 'Депутат ГД', 'SF' : 'Член СФ'}
    team_slice = df['position'] == names[team]

    return df[team_slice]


def get_faction(df, faction):

    faction_slice = df['curr_last_faction_id'] == str(faction)

    return df[faction_slice]


def fir(tou):
    return tou[0]


def parse_data(df):

    fac = list(set(zip(list(df['curr_last_faction']),
                       list(df['curr_last_faction_id']))))
    fac = sorted(fac, key=fir)

    tt = df['isCurrent'] == True
    ff = df['isCurrent'] == False

    curr_t = list(zip(list(df[tt]['name']),
                      list(df[tt]['ind'])))
    curr_t = sorted(curr_t, key=fir)
    curr_f = list(zip(list(df[ff]['name']),
                      list(df[ff]['ind'])))
    curr_f = sorted(curr_f, key=fir)

    return fac, curr_t, curr_f


def get_dep(mainurl, mytoken, myapptoken, ind):

    data = requests.get(mainurl + mytoken +
                        '/deputy.json?app_token=' +
                        myapptoken + '&id=' +
                        str(ind)).json()

    return data


def get_text(mainurl, mytoken, myapptoken, ind):
    url = (mainurl + mytoken +
           '/transcriptDeputy/' +
           str(ind) + '.json?app_token=' +
           myapptoken +
           '&limit=20&page=1')

    rj = requests.get(url).json()

    total = int(rj['totalCount'])
    if total / 20 > total // 20:
        num = total // 20 + 1
    else:
        num = total // 20

    data = [rj]

    for i in range(2, num + 1):
        rjs = requests.get(url).json()
        data.append(rjs)

    return data


def parse_text_data(textdata):
    data = []
    for td in textdata:
        for e in td['meetings']:
            cur_date = e['date']
            que = len(e['questions'])
            lines = []
            for q in e['questions']:
                for p in q['parts']:
                    for ind, l in enumerate(p['lines']):
                        if l.strip() == '':
                            lines.extend(p['lines'][ind:])
                            break

            lines = [l.strip() for l in lines if l.strip() != '']
            lines = ' '.join(lines).lower()

            c = [cur_date, lines, que]
            data.append(c)
    return data


@app.route('/')
def show_duma():

    fac, curr_t, curr_f, = parse_data(df)

    return render_template("Duma_main.html",
                           fac = fac,
                           curr_t = curr_t,
                           curr_f = curr_f,
                           sty = prl)


@app.route("/<team>")
def show_team(team):

    data = get_team(df, team)
    fac, curr_t, curr_f, = parse_data(data)
    if team == 'GD':
        sty = gd
    else:
        sty = sf

    return render_template("Duma_main.html",
                           fac = fac,
                           curr_t = curr_t,
                           curr_f = curr_f,
                           sty = sty)


@app.route("/faction/<int:faction>")
def show_faction(faction):

    data = get_faction(df, faction)
    fac, curr_t, curr_f = parse_data(data)

    return render_template("Duma_main.html",
                           fac = fac,
                           curr_t = curr_t,
                           curr_f = curr_f,
                           sty = prl)


@app.route("/deputat/<int:index>")
def show_deputat(index):

    data = get_dep(main_url, my_token,
                   my_app_token, index)

    if data:
        name = data['name']
        patronymic = data['patronymic']
        family = data['family']
        birthdate = data.get('birthdate', '—')
        if birthdate != '—':
            bd = datetime.strptime(birthdate, '%Y-%m-%d')
            birthdate = bd.strftime('%d.%m.%Y')
        credentialsStart = data.get('credentialsStart', '—')
        if credentialsStart != '—':
            sd = datetime.strptime(credentialsStart, '%Y-%m-%d')
            credentialsStart = sd.strftime('%d.%m.%Y')
        credentialsEnd = data.get('credentialsEnd', '—')
        if credentialsEnd != '—':
            ed = datetime.strptime(credentialsEnd, '%Y-%m-%d')
            credentialsEnd = ed.strftime('%d.%m.%Y')
        factionName = data.get('factionName', '—')
        factionRole = data.get('factionRole', '—')
        if factionRole != '—':
            factionRole = re.sub(r'\d+\s\b', r'', factionRole)
        factionRegion = data.get('factionRegion', '—')
        partyNameInstr = data.get('partyNameInstr', '—')
        lawcount = data.get('lawcount', '—')
        regions = data.get('regions', '—')

        with open('stop_words.txt', 'r', encoding='utf-8') as f:
            stopw = [e.strip() for e in f.readlines() if e.strip() != '']

        td = get_text(main_url, my_token, my_app_token, index)
        ff = parse_text_data(td)
        df = pd.DataFrame(ff)
        df = df.set_index(pd.to_datetime(df[0]))
        dff = list(df.groupby([df.index.year]))
        text_per_year = []
        for e in dff:
            y = e[0]
            t = ' '.join(e[1][1])
            q = sum(e[1][2])
            c = (y, t, q)
            text_per_year.append(c)
        pics = []
        wc = WordCloud(colormap='gist_heat', max_words=50, background_color='white',
                       prefer_horizontal=1, width=1000, height=500, stopwords=stopw)
        for text in text_per_year:
            wc.generate(text[1])
            v = wc.to_image()
            figfile = BytesIO()
            v.save(figfile, 'PNG')
            figfile.seek(0)
            figdata_png = base64.b64encode(figfile.getvalue())
            result = str(figdata_png)[2:-1]
            num_of_questions = text[2]
            c = (text[0], result, num_of_questions)
            pics.append(c)

        return render_template("Deputat_page.html",
                               name=name,
                               patronymic=patronymic,
                               family=family,
                               birthdate=birthdate,
                               credentialsStart=credentialsStart,
                               credentialsEnd=credentialsEnd,
                               factionName=factionName,
                               factionRole=factionRole,
                               factionRegion=factionRegion,
                               partyNameInstr=partyNameInstr,
                               lawcount=lawcount,
                               regions=regions,
                               pics=pics)
    else:
        return render_template("No_page.html")


if __name__ == "__main__":
    app.run(debug=False)