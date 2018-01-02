# Import Libraries
from flask import Flask, render_template, json, request, session
from flask.ext.mysql import MySQL
import os
import json

app = Flask(__name__)
mysql = MySQL()

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'myDB_TasosK'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# Global variables
conn = mysql.connect()
cursor = conn.cursor()
currentUser = ""

# Routes
@app.route("/")
def main():
    return render_template('index.html',currentUser=currentUser)

@app.route('/showSignUp')
def showSignUp():
    if not session.get('logged_in'):
        return render_template('signup.html')
    else:
        return main()
    
@app.route('/signUp',methods=['POST'])
def signUp():
    # Get values from the form
    username = request.form['inputUsername']
    password = request.form['inputPassword']
    fname = request.form['inputFirstName']
    lname = request.form['inputLastName']
    role = request.form['inputRole']
    
    # Ensure no fields are left empty
    if not (username == '' or password == '' or fname == '' or lname == '' or role == ''):
        # Call procedure to insert values into database
        cursor.callproc('createTeacher',(username,password,fname,lname,role))
        data = cursor.fetchall()
        
        if len(data) is 0:
            conn.commit()
            return main()
        else:
            return json.dumps({'Error:':str(data[0])})
    # If a field is empty, prompt user to try again
    else:
        return showSignUp()

@app.route('/showLogIn')
def showLogIn():
    if not session.get('logged_in'):
        # "Error" is an error message that appears when the user
        # attempts to log in with invalid credentials.
        # Leaving it blank in this case.
        return render_template('login.html',error='')
    else:
        return main()
        
@app.route('/login', methods=['POST'])
def logIn():
    username  = request.form['username']
    password  = request.form['password']
    
    # If username & password match in database, create session and log in
    if (cursor.execute("SELECT * FROM teacher WHERE t_username = '" + username + "' AND t_password = '" + password + "'")):
        conn.commit()
        session['logged_in'] = True
        # Set the currentUser variable to the given username
        global currentUser
        currentUser = username
        return main()
    else:
        # If credentials are invalid, 
        conn.commit()
        session['logged_in'] = False
        # Display an error message, prompting the user to try again
        return render_template('login.html',error="Invalid credentials. Try again.")

@app.route('/logout')
def logOut():
    if session.get('logged_in'):
        session['logged_in'] = False
        return main()
    else:
        return main()
        
# This function will be used primarily for selecting data from the database
def query_db(query, args=(), one=False):
    cursor.execute(query, args)
    rv = [dict((cursor.description[idx][0], value)
    for idx, value in enumerate(row)) for row in cursor.fetchall()]
    return (rv[0] if rv else None) if one else rv        

# The overview page displays all classes along with associated students & assignments
@app.route('/overview/', methods=['GET'])
def overview():
    if session.get('logged_in'):
        students = query_db("SELECT s_id,s_username,s_fname,s_lname,s_role,s_birthdate FROM student")
        classes = query_db("SELECT c_id,c_name,c_description FROM class")
        assignments = query_db("SELECT a_id,a_title,a_deadline,a_description,a_classid FROM assignment")
        enrollments = query_db("SELECT e_class,e_student FROM enrollment")
        return render_template('overview.html',students=students,classes=classes,assignments=assignments,enrollments=enrollments)
    else:
        return showLogIn()

# The profile page displays the currently logged in user's information
@app.route('/profile/', methods=['GET'])
def profile():
    if session.get('logged_in'):
        userData = query_db("SELECT t_id,t_username,t_password,t_fname,t_lname,t_role FROM teacher WHERE t_username = '" + currentUser + "'")
        return render_template('profile.html',userData=userData)
    else:
        return showLogIn()


@app.route('/profile/updateProfile')
def updateProfile():
    if session.get('logged_in'):
        return render_template('updateTeacher.html')
    else:
        return showLogIn()
        
@app.route('/commitUpdateTeacher',methods=['POST'])
def commitUpdateTeacher():
    # Enable usage of the currentUser variable, which will
    # need to be updated if the user changes their username.
    global currentUser
    # Get values from the form
    username = request.form['inputUsername']
    password = request.form['inputPassword']
    fname = request.form['inputFirstName']
    lname = request.form['inputLastName']
    role = request.form['inputRole']
    
    # Update each value individually, in case the user has left any blank values,
    # which means they don't wish to update them.
    query = "UPDATE teacher SET t_username = %s WHERE t_username = %s AND NOT %s = ''"
    cursor.execute(query,(username,currentUser,username))
    # If the user updated their username, update the currentUser variable
    if not(username == ''):
        currentUser = username
    query = "UPDATE teacher SET t_password = %s WHERE t_username = %s AND NOT %s = ''"
    cursor.execute(query,(password,currentUser,password))
    query = "UPDATE teacher SET t_fname = %s WHERE t_username = %s AND NOT %s = ''"
    cursor.execute(query,(fname,currentUser,fname))
    query = "UPDATE teacher SET t_lname = %s WHERE t_username = %s AND NOT %s = ''"
    cursor.execute(query,(lname,currentUser,lname))
    query = "UPDATE teacher SET t_role = %s WHERE t_username = %s AND NOT %s = ''"
    cursor.execute(query,(role,currentUser,role))
    
    data = cursor.fetchall()
    if len(data) is 0:
        conn.commit()
        return profile()
    else:
        return updateProfile()

# Enrollment allows teachers to assign students to a class
@app.route('/students/enrollStudent')
def showEnrollment():
    if session.get('logged_in'):
        return render_template('enrollStudent.html')
    else:
        return showLogIn()    

@app.route('/enroll',methods=['POST'])
def enroll():
    # Get values from the form
    _class = request.form['inputClass']
    student = request.form['inputStudent']
    
    # If the class and student exist, enroll the student
    if ((cursor.execute("SELECT * FROM class WHERE c_id = '" + _class + "'")) and (cursor.execute("SELECT * FROM student WHERE s_id = '" + student + "'"))):
        cursor.callproc('enrollStudent',(_class,student))
        
        data = cursor.fetchall()
        if len(data) is 0:
            conn.commit()
            return main()
        else:
            return showEnrollment()
    # If the class or student don't exist, show enrollment again
    else:
        return showEnrollment()

# Un-enrolling allows teachers to unassign students from a class        
@app.route('/students/unenrollStudent')
def showUnEnrollment():
    if session.get('logged_in'):
        return render_template('unenrollStudent.html')
    else:
        return showLogIn()
       
@app.route('/unenroll',methods=['POST'])
def unenroll():
    # read the posted values from the UI
    student = request.form['inputStudent']
    _class = request.form['inputClass']
    
    query = "DELETE FROM enrollment WHERE e_student = %s AND e_class = %s"
    cursor.execute(query, (student,_class))
    
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return showUnEnrollment()

# Shows a list of all teachers; unlike the other lists, this one is view-only
@app.route('/teachers/', methods=['GET'])
def teachers():
    if session.get('logged_in'):
        result = query_db("SELECT t_id,t_username,t_fname,t_lname,t_role FROM teacher")
        return render_template('teachers.html',table=result)
    else:
        return showLogIn()
 
# CLASSES
@app.route('/classes/', methods=['GET'])
def classes():
    if session.get('logged_in'):
        result = query_db("SELECT c_id,c_name,c_description FROM class")
        return render_template('classes.html',table=result)
    else:
        return showLogIn()

@app.route('/classes/showAddClass')
def showAddClass():
    if session.get('logged_in'):
        return render_template('createClass.html')
    else:
        return showLogIn()
    
@app.route('/addClass',methods=['POST'])
def addClass():
    # Get values from the form
    name = request.form['inputName']
    description = request.form['inputDescription']
    
    # Ensure no fields are left empty
    if not (name == '' or description == ''):
        cursor.callproc('createClass',(name,description))
        data = cursor.fetchall()
        
        if len(data) is 0:
            conn.commit()
            return main()
        else:
            return showAddClass()
    # If a field is empty, prompt user to try again
    else:
        return showAddClass()

       
@app.route('/classes/deleteClass')
def deleteClass():
    if session.get('logged_in'):
        return render_template('deleteClass.html')
    else:
        return  showLogIn()
       
@app.route('/deleteClassID',methods=['POST'])
def deleteClassID():
    # Get value from the form
    ID = request.form['inputID']
    
    # Also delete the class' enrollments
    query = "DELETE FROM enrollment WHERE e_class = %s"
    cursor.execute(query,ID)
    # And any assignments associated with it
    query = "DELETE FROM assignment WHERE a_classid = %s"
    cursor.execute(query,ID)
    query = "DELETE FROM class WHERE c_id = %s"
    cursor.execute(query,ID)
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return deleteClass()

@app.route('/deleteClassName',methods=['POST'])
def deleteClassName():
    # Get value from the form
    name = request.form['inputName']
    
    # Delete the class' enrollments; find it by searching the enrollment board where the ID matches the given name
    query = "DELETE FROM enrollment WHERE e_class = (SELECT c_id FROM class WHERE c_name = %s)"
    cursor.execute(query,name)
    # Delete the class' associated assignments, using the same method as above
    query = "DELETE FROM assignment WHERE a_classid = (SELECT c_id FROM class WHERE c_name = %s)"
    cursor.execute(query,name)
    query = "DELETE FROM class WHERE c_name = %s"
    cursor.execute(query,name)
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return deleteClass()
        
@app.route('/classes/updateClass')
def updateClass():
    if session.get('logged_in'):
        return render_template('updateClass.html')
    else:
        return showLogIn()

@app.route('/commitUpdateClass',methods=['POST'])
def commitUpdateClass():
    # Get values from the form
    ID = request.form['inputID']
    name = request.form['inputName']
    description = request.form['inputDescription']
    
    # Update fields that are not blank
    query = "UPDATE class SET c_name  = %s WHERE c_id = %s AND NOT %s = ''"
    cursor.execute(query,(name,ID,name))
    query = "UPDATE class SET c_description = %s WHERE c_id = %s AND NOT %s = ''"
    cursor.execute(query,(description,ID,description))
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return updateClass()

# ASSIGNMENTS
@app.route('/assignments/', methods=['GET'])
def assignments():
    if session.get('logged_in'):
        result = query_db("SELECT a_id,a_title,a_deadline,a_description,a_classid FROM assignment")
        return render_template('assignments.html',table=result)
    else:
        return showLogIn()

@app.route('/assignments/showAddAssignment')
def showAddAssignment():
    if session.get('logged_in'):
        return render_template('createAssignment.html')
    else:
        return showLogIn()
    
@app.route('/addAssignment',methods=['POST'])
def addAssignment():
    # Get values from the form
    title = request.form['inputTitle']
    deadline = request.form['inputDeadline']
    description = request.form['inputDescription']
    CID = request.form['inputCID']
    
    # Ensure no fields are left empty
    if not (title == '' or deadline == '' or description == '' or CID == ''):
    # Only create the assignment if the Class ID exists
        if (cursor.execute("SELECT * FROM class WHERE c_id = '" + CID + "'")):
            cursor.callproc('createAssignment',(title,deadline,description,CID))
            data = cursor.fetchall()
            if len(data) is 0:
                conn.commit()
                return main()
            else:
                return showAddAssignment()
        # If the Class ID doesn't exist, prompt the user to try again
        else:
            return showAddAssignment()
    # If a field is empty, prompt user to try again
    else:
        return showAddAssignment()

       
@app.route('/assignments/deleteAssignment')
def deleteAssignment():
    if session.get('logged_in'):
        return render_template('deleteAssignment.html')
    else:
        return showLogIn()
       
@app.route('/deleteAssignmentID',methods=['POST'])
def deleteAssignmentID():
    # Get values from the form
    ID = request.form['inputID']
    
    query = "DELETE FROM assignment WHERE a_id = %s"
    cursor.execute(query,ID)
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return deleteAssignment()

@app.route('/deleteAssignmentName',methods=['POST'])
def deleteAssignmentName():
    # Get values from the form
    title = request.form['inputTitle']
    
    query = "DELETE FROM assignment WHERE a_title = %s"
    cursor.execute(query,title)
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return deleteAssignment()
        
@app.route('/assignments/updateAssignment')
def updateAssignment():
    if session.get('logged_in'):
        return render_template('updateAssignment.html')
    else:
        return showLogIn()

@app.route('/commitUpdateAssignment',methods=['POST'])
def commitUpdateAssignment():
    # Get values from the form
    ID = request.form['inputID']
    title = request.form['inputTitle']
    deadline = request.form['inputDeadline']
    description = request.form['inputDescription']
    CID = request.form['inputCID']
    
    # Update fields that are not blank
    query = "UPDATE assignment SET a_title  = %s WHERE a_id = %s AND NOT %s = ''"
    cursor.execute(query,(title,ID,title))
    query = "UPDATE assignment SET a_deadline = %s WHERE a_id = %s AND NOT %s = ''"
    cursor.execute(query,(deadline,ID,deadline))
    query = "UPDATE assignment SET a_description = %s WHERE a_id = %s AND NOT %s = ''"
    cursor.execute(query,(description,ID,description))
    # Update the class only if its ID exists
    if (cursor.execute("SELECT * FROM class WHERE c_id = '" + CID + "'")):
        query = "UPDATE assignment SET a_classid = %s WHERE a_id = %s AND NOT %s = ''"
        cursor.execute(query,(CID,ID,CID))
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return updateAssignment()

# STUDENTS
@app.route('/students/', methods=['GET'])
def students():
    if session.get('logged_in'):
        result = query_db("SELECT s_id,s_username,s_password,s_fname,s_lname,s_role,s_birthdate FROM student")
        return render_template('students.html',table=result)
    else:
        return showLogIn()
        
@app.route('/students/showAddStudent')
def showAddStudent():
    if session.get('logged_in'):
        return render_template('createStudent.html')
    else:
        return showLogIn()
    
@app.route('/addStudent',methods=['POST'])
def addStudent():
    # Get values from the form
    username = request.form['inputUsername']
    password = request.form['inputPassword']
    fname = request.form['inputFirstName']
    lname = request.form['inputLastName']
    role = request.form['inputRole']
    birthdate = request.form['inputBirthdate']
    
    # Ensure no fields are left empty
    if not (username == '' or password == '' or fname == '' or lname == '' or role == '' or birthdate == ''):
        cursor.callproc('createStudent',(username,password,fname,lname,role,birthdate))
        data = cursor.fetchall()
        
        if len(data) is 0:
            conn.commit()
            return main()
        else:
            return showAddStudent()
    # If a field is empty, prompt user to try again
    else:
        return showAddStudent()
       
@app.route('/students/deleteStudent')
def deleteStudent():
    if session.get('logged_in'):
        return render_template('deleteStudent.html')
    else:
        return showLogIn()
       
@app.route('/deleteStudentID',methods=['POST'])
def deleteStudentID():
    # Get value from the form
    ID = request.form['inputID']
    
    # Also delete their enrollments
    query = "DELETE FROM enrollment WHERE e_student = %s"
    cursor.execute(query,ID)
    query = "DELETE FROM student WHERE s_id = %s"
    cursor.execute(query,ID)
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return deleteStudent()

@app.route('/deleteStudentName',methods=['POST'])
def deleteStudentName():
    # Get value from the form
    username = request.form['inputUsername']
    
    # Delete their enrollment; find it by searching the student board where the ID matches the given username
    query = "DELETE FROM enrollment WHERE e_student = (SELECT s_id FROM student WHERE s_username = %s)"
    cursor.execute(query,username)
    query = "DELETE FROM student WHERE s_username = %s"
    cursor.execute(query,username)
    
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return deleteStudent()
        
@app.route('/students/updateStudent')
def updateStudent():
    if session.get('logged_in'):
        return render_template('updateStudent.html')
    else:
        return showLogIn()

@app.route('/commitUpdateStudent',methods=['POST'])
def commitUpdateStudent():
    # Get values from the form
    ID = request.form['inputID']
    username = request.form['inputUsername']
    password = request.form['inputPassword']
    fname = request.form['inputFirstName']
    lname = request.form['inputLastName']
    role = request.form['inputRole']
    birthdate = request.form['inputBirthdate']
    
    # Update the fields that are not blank
    query = "UPDATE student SET s_username = %s WHERE s_id = %s AND NOT %s = ''"
    cursor.execute(query,(username,ID,username))
    query = "UPDATE student SET s_password = %s WHERE s_id = %s AND NOT %s = ''"
    cursor.execute(query,(password,ID,password))
    query = "UPDATE student SET s_fname = %s WHERE s_id = %s AND NOT %s = ''"
    cursor.execute(query,(fname,ID,fname))
    query = "UPDATE student SET s_lname = %s WHERE s_id = %s AND NOT %s = ''"
    cursor.execute(query,(lname,ID,lname))
    query = "UPDATE student SET s_role = %s WHERE s_id = %s AND NOT %s = ''"
    cursor.execute(query,(role,ID,role))
    query = "UPDATE student SET s_birthdate = %s WHERE s_id = %s AND NOT %s = ''"
    cursor.execute(query,(birthdate,ID,birthdate))
    data = cursor.fetchall()
    
    if len(data) is 0:
        conn.commit()
        return main()
    else:
        return updateStudent()

# Run App
if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run()