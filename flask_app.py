##### Imports etc

from flask import Flask, render_template, redirect, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from PIL import Image, ImageFont, ImageDraw
from datetime import date, datetime, timedelta

from flask_sslify import SSLify
import os
import shutil
import json
# import csv

app = Flask(__name__)

app.config.from_object('config')

sslify = SSLify(app)
mail=Mail(app)
db = SQLAlchemy(app)

from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import BooleanField, StringField,  HiddenField # validators, IntegerField
from wtforms.validators import DataRequired, InputRequired, Length, Email
from werkzeug.security import pbkdf2_hex


saltx =app.config['SALTX']
adressatenvars =app.config['ADRESSATENSAMMLUNG']
imagesource1 =app.config['BLUEPRINT1']
imagesource2 =app.config['BLUEPRINT2']

varimage = os.path.join(app.instance_path, imagesource1)
varimage2 = os.path.join(app.instance_path, imagesource2)
Image.warnings.simplefilter('error', Image.DecompressionBombWarning) # activate additional defense against decompressionbombs

##### Models


class Dateneingabe(FlaskForm):
    Ausweisbild = FileField('Lichtbildausweis hochladen (aktiviert Kamera-App/Fotogalerie auf Smartphone)', validators=[FileRequired(),FileAllowed(['jpeg','jpg', 'png', 'gif'], '.jpeg .gif and .png files only!')])
    email = StringField('Email Adresse', validators=[InputRequired(), Email(), Length(min=1, max=77)])
    Vorname = StringField('Vorname', validators=[InputRequired(), Length(min=1, max=77)])
    Nachname = StringField('Nachname', validators=[InputRequired(), Length(min=1, max=77)])
    Gebdatum = StringField('Geburtsdatum', validators=[InputRequired(), Length(min=1, max=25)])
    Strasse = StringField('Strasse', validators=[InputRequired(), Length(min=1, max=77)])
    Plz = StringField('PLZ', validators=[InputRequired(), Length(min=4, max=15)])
    Strassealt = StringField('(Optional)Früherer Wohnort: Strasse', validators=[ Length(min=0, max=25)])
    Plzalt = StringField('(Optional)Früherer Wohnort: PLZ', validators=[Length(min=0, max=15)])
    Nachnamealt = StringField('(Optional)Früherer Nachname', validators=[Length(min=0, max=15)])
    Firmenauswahldaten = HiddenField('Firmenauswahldaten',validators=[DataRequired()])

class mailliste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dbdatum = db.Column(db.DateTime, nullable=False,default=datetime.utcnow)
    dbemail = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<mailliste %r>' % self.dbemail

##### Routing


@app.route('/datenanfrage', methods=['GET','POST'])
def anfrageformular():
    cl = request.content_length

    if cl is not None and cl > 30 * 1024 * 1024:
        abort(413)

    if request.method == 'POST' and len(request.form)>0 and len(request.form)<50:

        for ersteintrag in adressatenvars:
            if adressatenvars[ersteintrag]['extrafeld'] is not False:
                if ersteintrag in request.form:
                    setattr(Dateneingabe, ersteintrag, StringField(adressatenvars[ersteintrag]['extrafeld'],validators=[InputRequired(), Length(min=1, max=25)]))
                else:
                    try:
                        delattr(Dateneingabe, ersteintrag)
                    except:
                        print(ersteintrag+' war nicht angelegt')

        setattr(Dateneingabe, 'recaptcha', RecaptchaField())
        setattr(Dateneingabe, 'accept_agb', BooleanField('Ich habe die AGB gelesen', validators=[DataRequired()]))


        form=Dateneingabe()

        if request.args.get('q')=='send' and form.validate_on_submit() :
            if mailnotusedwithinayear(form.email.data,False):
                tempinquiryid=form.csrf_token.data

                try: # sanitize uploaded picture
                    filename = "ausweis.jpg"
                    with Image.open(form.Ausweisbild.data) as im: # Resize
                        im.thumbnail((400, 400), Image.ANTIALIAS)
                        os.makedirs(os.path.join(app.instance_path, tempinquiryid))
                        im.save(os.path.join(app.instance_path,tempinquiryid,filename), "JPEG")
                except:
                    abort(415)

                firmen=[]
                for i in form.Firmenauswahldaten.data.split("'"):
                    if i in adressatenvars: #umgekehrt iterieren
                        firmen.append(i)
                        try:
                            property_name = getattr(form, i)
                            extrafelddaten=property_name.data
                        except:
                            extrafelddaten=False
                        makedatainquiry(form,i,tempinquiryid,extrafelddaten)

                inquirydoc= [firmen,form.email.data,form.Vorname.data+' '+form.Nachname.data] #für task
                inquirydocfile=os.path.join(app.instance_path,tempinquiryid,'inquirydoc.json') #für task als temp abspeichern und dann renamen
                with open(inquirydocfile, 'w') as inquiryfile: #für task
                    json.dump(inquirydoc, inquiryfile) #für task

                if mailnotusedwithinayear(form.email.data,True): #save hashed mail in order to block it for one year
                    print("Angelegt: "+ tempinquiryid)

                return redirect('/static/senden.html', code=302)
            else:
                return "Fehler: Möglicherweise haben Sie dieses Service schon einmal innerhalb der letzten 365 Tage genutzt."

        if request.args.get('q')=='go':
            form.Firmenauswahldaten.data=list(request.form.keys())#bei validation error firmenauswahldaten übergeben

        return render_template('anfrageformular.html', gewaehltefirmenids_list = request.form, form=form)
    print('Fehler: falscher request')
    return redirect("/static/index.html", code=302)


@app.route('/impressum.html')
def impressum():
    return redirect("/static/impressum.html", code=302)


@app.route('/')
@app.route('/index.html')
@app.route('/index')
@app.route('/instance/')
def index():
    return redirect("/static/index.html", code=302)


@app.errorhandler(404)
def page_not_found(e):
    return redirect("/static/index.html", code=302)


@app.route('/hsfd897-32hudsh3-28hewu-nfh3289n') #trigger sending of inquiries
def launchmails():
    try:
        for f in os.listdir(app.instance_path):
            child = os.path.join(app.instance_path, f)
            if os.path.isdir(child):
                inquirydocfile=os.path.join(app.instance_path,f,'inquirydoc.json')
                with open(inquirydocfile, 'r') as inquiryfile: #für task
                    inquiryjson = json.loads(inquiryfile)
                sendinquirymails(inquiryjson[0],f,inquiryjson[1],inquiryjson[2])
                return 'ok'
    except:
        return "nothing done"


##### functions for generating sending and deleting inquiries


def mailnotusedwithinayear(mailausformular,updatego): # check if this service has already been used with a mailadress within a year
    checkmail=pbkdf2_hex(mailausformular, saltx, iterations=50000, keylen=None, hashfunc=None)
    checkentry=mailliste.query.filter_by(dbemail=checkmail).first()
    yearcheck = timedelta(days=365)
    if checkentry is None or checkentry.dbdatum<(datetime.utcnow()-yearcheck):
        if updatego:
            if checkentry is None:
                neueintrag = mailliste(dbemail=checkmail)
                db.session.add(neueintrag)
            else:
                checkentry.dbdatum=datetime.utcnow()
            db.session.commit()
            db.session.close()
        return True
    else:
        db.session.close()
        return False


def makedatainquiry(form,firma,inquiryid,extrafelddaten): # generate inquiries

    varadresse = adressatenvars[firma]['adresse']
    vardatum = date.today().strftime("%d/%m/%y")
    varnachname=form.Nachname.data
    varvorname=form.Vorname.data
    varname=varvorname+" " +varnachname
    vargebdatum=form.Gebdatum.data
    varemailadr=form.email.data
    varaktuellestr=form.Strasse.data
    varaktuelleplz=form.Plz.data
    varaktuelleanschrift=varaktuellestr+" " +varaktuelleplz
    varabisherigestr=form.Strassealt.data
    varabisherigeplz=form.Plzalt.data
    varbisherigernachname=form.Nachnamealt.data
    varabisherigeanschrift=varabisherigestr+varabisherigeplz
    varantragsteller=varvorname+"\n" +varnachname+"\n"+vargebdatum+"\n"+varemailadr+"\n"+varaktuelleanschrift+"\n"+varabisherigeanschrift+"\n"+varbisherigernachname

    dateiname0=os.path.join(app.instance_path,"open-sans.regular.ttf")
    fontobj = ImageFont.truetype(dateiname0, 28)

    # Anschreiben Teil 1 auffüllen

    imobjorig = Image.open(varimage).convert('RGBA')
    imobjtxt = Image.new('RGBA', (1000,280), (255,255,255,255))
    imobjsign = Image.new('RGBA', (1000,50), (255,255,255,255))

    drawobjtxt = ImageDraw.Draw(imobjtxt)
    drawobjtxt.multiline_text((0,0), varadresse, fill="black", font=fontobj, anchor=None, spacing=5, align="left")
    imobjorig.paste(imobjtxt, (320, 160))

    drawobjsign = ImageDraw.Draw(imobjsign)
    drawobjsign.text((0,0), varname, fill="black", font=fontobj, anchor=None, spacing=5, align="left")
    imobjorig.paste(imobjsign, (255, 1900))
    filenamejpg1=firma+"scan1.jpg"
    imagevar= os.path.join(app.instance_path,inquiryid,filenamejpg1)
    imobjorig.save(imagevar, "JPEG")

    #Anschreiben Teil 2 auffüllen

    imobjorig2 = Image.open(varimage2).convert('RGBA')

    if extrafelddaten is not False:
        varantragsteller=varantragsteller+"\n"+extrafelddaten


    imobjantragsteller = Image.new('RGBA', (800,600), (255,255,255,255))
    drawobjtxt2 = ImageDraw.Draw(imobjantragsteller)
    drawobjtxt2.multiline_text((0,0), varantragsteller, fill="black", font=fontobj, anchor=None, spacing=46, align="left")
    imobjorig2.paste(imobjantragsteller, (800, 770))

    imobjorig2.paste(imobjtxt, (320, 160))

    imobjdate = Image.new('RGBA', (300,50), (255,255,255,255))
    drawobjdate = ImageDraw.Draw(imobjdate)
    drawobjdate.text((0,0), vardatum, fill="black", font=fontobj, anchor=None, spacing=5, align="left")
    imobjorig2.paste(imobjdate, (400, 1768))
    filenamejpg2=firma+"scan2.jpg"
    imagevar2= os.path.join(app.instance_path,inquiryid,filenamejpg2)
    imobjorig2.save(imagevar2, "JPEG")

    # csv fuer API
    #if adressatenvars[firma]['api'] == "csv":
    #    csvfirma=firma+".csv"
    #    csvdatei= os.path.join(app.instance_path,inquiryid,csvfirma)
    #    if extrafelddaten is False or None:
    #        extrafelddaten ='keine'
    #    with open(csvdatei, 'w', newline='') as f:
    #        writer = csv.writer(f)
    #        writer.writerow(['Vorname','Nachname','Früherer Nachname','Geburtsdatum','Mailadresse','Anschrift','PLZ','Frühere Anschrift','Frühere PLZ','Kundennummer']
    #        writer.writerow([varvorname,varnachname,varbisherigernachname,vargebdatum,varemailadr,varaktuellestr,varaktuelleplz,varabisherigestr,varabisherigeplz,extrafelddaten])



def sendinquirymails(firmen,inquiryid,ccmail,varname):  # send inquiries
    try:
        with mail.connect() as conn:
            for firma in firmen:
                mailadresse=adressatenvars[firma]['email']

                filenamejpg1=firma+"scan1.jpg"
                imagevar= os.path.join(app.instance_path,inquiryid,filenamejpg1)

                filenamejpg2=firma+"scan2.jpg"
                imagevar2= os.path.join(app.instance_path,inquiryid,filenamejpg2)

                ausweisbild2= os.path.join(app.instance_path,inquiryid,"ausweis.jpg")

                message = '''Sehr geehrte Damen und Herren,

                {0} hat diese E-Mail generiert, um Ihnen ein DSGVO-Auskunftsersuchen zu übermitteln.
                Bitte senden Sie Ihre Antworten an: {1}

                Mit höflicher Bitte um Erledigung.
                Beste Grüße.'''
                message=message.format(varname,ccmail)

                subject = "Datenauskunft nach Art 15 DSGVO"
                msg = Message(recipients=[mailadresse],cc=[ccmail],reply_to=ccmail,body=message,subject=subject)

                #if adressatenvars[firma]['api'] == "csv":
                #    csvfirma=firma+".csv"
                #    csvdatei= os.path.join(app.instance_path,inquiryid,csvfirma)
                #    with app.open_resource(csvdatei) as fp:
                #        msg.attach("anfrage.csv", "text/csv", fp.read())

                with app.open_resource(imagevar) as fp:
                    msg.attach("scan1.jpg", "image/jpg", fp.read())
                with app.open_resource(imagevar2) as fp:
                    msg.attach("scan2.jpg", "image/jpg", fp.read())
                with app.open_resource(ausweisbild2) as fp:
                    msg.attach("ausweis.jpg", "image/jpg", fp.read())

                conn.send(msg)
            deleteinquiries(inquiryid)
        print('gesendet')
        return 'ok' #True
    except:
        deleteinquiries(inquiryid)
        return False



def deleteinquiries(inquiryid): #delete inquiries
    inquiryidfull= os.path.join(app.instance_path,inquiryid)
    try:
        shutil.rmtree(inquiryidfull)
        print("Gelöscht: "+inquiryidfull)
    except:
        print("Unlöschbar: "+inquiryidfull)


