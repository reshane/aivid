import os
import shutil
from app import app, db
import urllib.request
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from models import Entry
import json
from fastai.vision.all import *
from datetime import datetime

def label_func(f): return f[0] == 'p'
def acc_camvid(*_): pass
def get_y(*_): pass

model = "my_export.pkl"
learn = load_learner(os.path.join(app.config['MODEL_FOLDER'], model))

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

logfile = "uploads.log"

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def upload_form():
	return render_template('upload.html')

@app.route('/classify', methods=["POST"])
def classify():
	imagefile = request.files.get('imagefile', '')
	filename = imagefile.filename
	imagefile.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	print(imagefile.filename)
	prediction = learn.predict(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	print(prediction)
	return str(prediction)

def parsebase(result):
	print(str(result[0]) + " " + str(result[1]) + " " + str(result[2]))
	percentage = result[2][0]
	if result[0] == "True":
		percentage = result[2][1]
	print(percentage)
	resultstring = ("This is Poison Ivy", percentage*100)
	if result[0] == "False":
		resultstring = ("This is not Poison Ivy", percentage*100)	
	return resultstring[0]+ " " + str(resultstring[1])[str(resultstring[1]).index("(")+1:str(resultstring[1]).index(")")] + "%"

def log(event):
	file = open(logfile, "a")
	now = datetime.now()
	file.write("\n" + now.strftime("%d/%m/%Y %H:%M:%S") + " " + event)
	file.close()


@app.route('/', methods=['POST'])
def upload_image():
	if 'file' not in request.files:
		flash('No file part')
		return redirect(request.url)
	file = request.files['file']
	if file.filename == '':
		flash('No image selected for uploading')
		return redirect(request.url)
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		image = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		image = image.convert("RGB")
		new_height = 300
		new_image = image.resize((min(int(image.width * float(new_height / image.height)), new_height), new_height))
		os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		newfilename = filename[0:filename.index('.')] + ".jpg"
		new_image.save(os.path.join(app.config['UPLOAD_FOLDER'], newfilename))
		res = learn.predict(os.path.join(app.config['UPLOAD_FOLDER'], newfilename))
		resultstring = parsebase(res)
		# flash(res)
		# flash(resultstring)
		# flash(newfilename)
		log(str(filename + " uploaded and stored " + os.path.join(app.config['UPLOAD_FOLDER'], filename)))
		log(os.path.join(app.config['UPLOAD_FOLDER'], filename) + " => " + str(res))
		print(res[2][0])
		if res[2][0] < 0.7 and res[2][0] > 0.3:
			print("here")
			return render_template('upload.html', filename=newfilename, results=(str(res), resultstring, newfilename), contestable=True)
		print("here, no contest")
		return render_template('upload.html', filename=newfilename, results=(str(res), resultstring, newfilename))
	else:
		flash('Allowed image types are -> png, jpg, jpeg, gif')
		return redirect(request.url)

@app.route('/display/<filename>')
def display_image(filename):
	#print('display_image filename: ' + filename)
	return redirect(url_for('static', filename='uploads/' + filename), code=301)

@app.route('/about', methods=['GET'])
def about():
	return render_template('about.html')

@app.route('/contest', methods=['GET', 'POST'])#make it postable as well, so that you can add a new one to the list, then display
def contest():
	if request.method == 'POST':
		new_entry = Entry(file=request.form.get('filename'), result=request.form.get('result'), upvotes=request.form.get('upvotes'))
		#print(Entry.query.all())
		for e in Entry.query.all():
			#print("here")
			if e.file == request.form.get('filename'):
				#print(e.file)
				flash("Image already contested")
				return render_template('contest.html', entries=Entry.query.all())
		db.session.add(new_entry)
		db.session.commit()
		#print(Entry.query.all())
		log(request.form.get('filename') + " contested with result of " + request.form.get('result'))
	
	return render_template('contest.html', entries=Entry.query.all())

@app.route('/vote', methods=['POST'])
def vote():
	# 1 = uphold -1, 0 = overturn +1
	# id, vote
	entry = Entry.query.get(request.form.get('id'))
	#print(request.form.get('vote') == "1")
	if request.form.get('vote') == "0":
		entry.upvotes = entry.upvotes - 1
	elif request.form.get('vote') == "1":
		entry.upvotes = entry.upvotes + 1

	if entry.upvotes > 10:
		entry.in_review = False
		move_file(entry)
		#here we've overturned our classification
	elif entry.upvotes < -10:
		entry.inreview = False
		#here we've confirmed our classification

	db.session.commit()
	# here we need to do something
	return redirect('/contest', code=301)#render_template('contest.html', entries=Entry.query.all())

def move_file(entry):
	#print(entry.file)
	#name poison-ivy something if the result was False and upvotes > 10
	#print(entry.result)
	new_path = os.path.join(app.config['OVERTURN_FOLDER_TRUE'], entry.file)
	if (entry.result)[2] == 'T':
		os.path.join(app.config['OVERTURN_FOLDER_FALSE'], entry.file)
	shutil.move(os.path.join(app.config['UPLOAD_FOLDER'], entry.file), new_path)#("path/to/current/file.foo", "path/to/new/destination/for/file.foo")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)