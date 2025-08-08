from flask import Flask, render_template, redirect

app = Flask(__name__)

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/location')
def location_redirect():
    return redirect("http://localhost:5003", code=302)

@app.route('/linkedin')
def linkedin_redirect():
    return redirect("http://localhost:8081", code=302)

@app.route('/insights')
def insights_redirect():
    return redirect("http://localhost:5001", code=302)  # or wherever your 3rd tool is running


if __name__ == '__main__':
    app.run(port=5000, debug=True)
