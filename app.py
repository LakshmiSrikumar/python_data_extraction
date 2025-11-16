from flask import Flask, render_template


from supabase_client import supabase
app = Flask(__name__)

@app.route("/")
def index():
    # Fetch all records from Supabase
    response = supabase.table("da_records").select("*").execute()
    data = response.data
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)
