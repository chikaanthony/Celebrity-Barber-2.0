"""
Celebrity Barber Flask Application
With Firebase Database Integration
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.secret_key = 'your-secret-key-change-in-production'

# Firebase Configuration
# Replace with your actual Firebase service account JSON
FIREBASE_CONFIG = {
    'apiKey': "YOUR_API_KEY",
    'authDomain': "YOUR_PROJECT.firebaseapp.com",
    'projectId': "YOUR_PROJECT_ID",
    'storageBucket': "YOUR_PROJECT.appspot.com",
    'messagingSenderId': "YOUR_SENDER_ID",
    'appId': "YOUR_APP_ID",
    'databaseURL': "https://YOUR_PROJECT.firebaseio.com"
}

# Initialize Firebase
try:
    # Use service account JSON file
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully!")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    db = None


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def normalize_referral_code(code):
    return str(code or '').strip().upper()


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login
    Authenticates user and redirects to client dashboard
    """
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            print(f"Login attempt - Email: {email}, Password: {password}")
            
            # Check for admin credentials
            if email == 'chikaanthony896@gmail.com' and password == 'adminFIdelis242':
                session['user_id'] = 'admin'
                session['email'] = email
                session['user_name'] = 'Admin User'
                session['is_admin'] = True
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin'))
            
            if not email or not password:
                flash('Please enter email and password!', 'error')
                return redirect(url_for('login'))
            
            # Get user by email from Firebase Auth
            user = auth.get_user_by_email(email)
            
            # Check Firestore for user data
            if db:
                user_doc = db.collection('users').document(user.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    session['user_id'] = user.uid
                    session['email'] = user.email
                    session['user_name'] = user_data.get('full_name', 'User')
                    session['is_admin'] = user_data.get('is_admin', False)
                    flash('Login successful!', 'success')
                    return redirect(url_for('clientdashboard'))
                else:
                    flash('User data not found. Please sign up first.', 'error')
            else:
                session['user_id'] = user.uid
                session['email'] = user.email
                session['user_name'] = user.display_name or 'User'
                session['is_admin'] = False
                flash('Login successful!', 'success')
                return redirect(url_for('clientdashboard'))
                
        except auth.UserNotFoundError:
            flash('User not found. Please sign up first.', 'error')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f'Login error: {e}')
            flash(f'Login error: {str(e)}', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/signup')
def signup():
    return render_template('signup.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration
    Creates user in Firebase Auth and stores data in Firestore
    """
    if request.method == 'POST':
        try:
            # 1. Grab data from HTML form
            name = request.form.get('full_name')
            email = request.form.get('email')
            pin = request.form.get('pin')  # Secure PIN as password
            phone = request.form.get('phone')
            referral_code = normalize_referral_code(request.form.get('referral_code', ''))
            
            print(f"Received: name={name}, email={email}, pin={pin}, phone={phone}")
            
            # Validate required fields
            if not name or not email or not pin:
                flash('All fields are required!', 'error')
                return redirect(url_for('signup'))
            
            if len(pin) < 6:
                flash('PIN must be at least 6 characters!', 'error')
                return redirect(url_for('signup'))
            
            # 2. Create user in Firebase Auth (for login)
            print("Creating user in Firebase...")
            user = auth.create_user(
                email=email,
                password=pin,
                display_name=name
            )
            print(f"User created: {user.uid}")
            
            # 3. Save user profile in Firestore (for dashboard)
            if db:
                user_data = {
                    'full_name': name,
                    'email': email,
                    'phone': phone,
                    'is_vip': False,
                    'total_spent': 0,
                    'referral_code': 'CELEB-' + user.uid[:4].upper(),
                    'referral_count': 0,
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                
                # If user used a referral code, link and increment referrer count
                if referral_code:
                    try:
                        referrers = db.collection('users').where('referral_code', '==', referral_code).limit(1).get()
                        if referrers:
                            referrer_id = referrers[0].id
                            user_data['used_referral_code'] = referral_code
                            db.collection('users').document(referrer_id).update({
                                'referral_count': firestore.Increment(1)
                            })
                            print(f"Incremented referral count for {referrer_id}")
                        else:
                            print(f"Referral code not found: {referral_code}")
                    except Exception as e:
                        print(f"Error updating referrer: {e}")
                
                db.collection('users').document(user.uid).set(user_data)
                print("Saved to Firestore!")
            
            # Create session
            session['user_id'] = user.uid
            session['email'] = user.email
            session['user_name'] = name
            session['is_admin'] = False
            
            flash('Success! You are now a Celebrity.', 'success')
            return redirect(url_for('clientdashboard'))
            
        except auth.EmailAlreadyExistsError:
            flash('Error: Email already exists!', 'error')
            return redirect(url_for('signup'))
            
        except Exception as e:
            print(f"Registration error: {e}")
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')


@app.route('/clientdashboard')
@login_required
def clientdashboard():
    # Get user data from Firestore
    user_id = session.get('user_id')
    user_data = None
    
    if db:
        try:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
        except Exception as e:
            print(f"Error fetching user data: {e}")
    
    return render_template('clientdashboard.html', user=user_data)


@app.route('/bookings')
@login_required
def bookings_page():
    """User booking history page"""
    return render_template('bookings.html')


@app.route('/referrals')
@login_required
def referrals_page():
    """User referral history page"""
    return render_template('referrals.html')


@app.route('/transactions')
@login_required
def transactions_page():
    """User transaction history page"""
    return render_template('transactions.html')


@app.route('/bookcut')
@login_required
def bookcut():
    return render_template('bookcut.html')


@app.route('/joinvip')
@login_required
def joinvip():
    return render_template('joinvip.html')


@app.route('/api/book', methods=['POST'])
@login_required
def create_booking():
    """Store a new booking in Firestore"""
    data = request.get_json()
    user_id = session.get('user_id')
    user_email = session.get('email')
    user_name = session.get('user_name')
    
    if db:
        try:
            booking_data = {
                'user_id': user_id,
                'user_email': user_email,
                'user_name': user_name,
                'service': data.get('service'),
                'price': data.get('price'),
                'date': data.get('date'),
                'requests': data.get('requests', ''),
                'receipt': data.get('receipt', ''),  # base64 receipt image
                'status': 'pending',  # pending, confirmed, completed, cancelled
                'type': 'booking',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # Add to bookings collection
            booking_ref = db.collection('bookings').document()
            booking_ref.set(booking_data)
            
            return {'success': True, 'message': 'Booking submitted successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/vip', methods=['POST'])
@login_required
def join_vip():
    """Store VIP request in Firestore as pending approval"""
    data = request.get_json()
    user_id = session.get('user_id')
    user_email = session.get('email')
    user_name = session.get('user_name')
    
    if db:
        try:
            # Add to approvals collection for admin to review
            approval_data = {
                'user_id': user_id,
                'user_email': user_email,
                'user_name': user_name,
                'type': 'vip',
                'amount': 2500,
                'receipt': data.get('receipt', ''),  # base64 receipt image
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('approvals').add(approval_data)
            
            return {'success': True, 'message': 'VIP request submitted for approval'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/user/spending')
@login_required
def get_user_spending():
    """Get user's total spending from approved/confirmed bookings"""
    user_id = session.get('user_id')
    
    if db:
        try:
            # Calculate from approved/confirmed bookings (more accurate)
            bookings = db.collection('bookings').where('user_id', '==', user_id).get()
            total_spent = 0
            for doc in bookings:
                data = doc.to_dict()
                status = data.get('status', '')
                # Only count approved or confirmed bookings
                if status not in ['approved', 'confirmed']:
                    continue
                amount = data.get('price') or data.get('amount') or 0
                if amount:
                    # Convert to number if it's a string
                    if isinstance(amount, str):
                        try:
                            amount = int(amount.replace(',', '').replace('ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¦', ''))
                        except:
                            amount = 0
                    total_spent += amount
            return {'success': True, 'total_spent': total_spent}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/refer')
@login_required
def refer():
    return render_template('refer.html')


@app.route('/reviews')
@login_required
def reviews():
    return render_template('review.html')


# Reviews API
@app.route('/api/reviews')
def get_reviews():
    """Get all reviews"""
    if db:
        try:
            # Try with ordering first
            reviews_ref = db.collection('reviews').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(20).get()
            review_list = []
            for doc in reviews_ref:
                data = doc.to_dict()
                data['id'] = doc.id
                review_list.append(data)
            return {'success': True, 'data': review_list}
        except Exception as e:
            print(f"Error fetching reviews with order: {e}")
            # Fallback: get reviews without ordering
            try:
                reviews_ref = db.collection('reviews').limit(20).get()
                review_list = []
                for doc in reviews_ref:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    review_list.append(data)
                # Sort locally by createdAt
                review_list.sort(key=lambda x: x.get('createdAt', 0), reverse=True)
                return {'success': True, 'data': review_list}
            except Exception as e2:
                print(f"Error fetching reviews: {e2}")
                return {'success': True, 'data': []}
    return {'success': True, 'data': []}


@app.route('/api/reviews/submit', methods=['POST'])
@login_required
def submit_review():
    """Submit a new review"""
    data = request.get_json()
    content = data.get('content', '')
    
    if not content:
        return {'success': False, 'message': 'Review content is required'}, 400
    
    user_id = session.get('user_id')
    
    if db:
        try:
            # Get user info
            user_doc = db.collection('users').document(user_id).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            
            # Create review
            review_data = {
                'content': content,
                'user_id': user_id,
                'name': user_data.get('name', user_data.get('email', 'Anonymous').split('@')[0]),
                'email': user_data.get('email', ''),
                'likes': 0,
                'replies': 0,
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            
            db.collection('reviews').add(review_data)
            return {'success': True, 'message': 'Review submitted successfully'}
        except Exception as e:
            print(f"Error submitting review: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/leaderboard')
@login_required
def leaderboard():
    return render_template('leaderboard.html')


# Leaderboard API
@app.route('/api/leaderboard')
@login_required
def get_leaderboard():
    """Get top spenders for leaderboard based on bookings"""
    if db:
        try:
            # Get all bookings
            bookings_ref = db.collection('bookings').get()
            
            # Aggregate spending by user
            user_spending = {}
            for doc in bookings_ref:
                data = doc.to_dict()
                user_id = data.get('user_id')
                # Only count approved or confirmed bookings
                status = data.get('status', '')
                if status not in ['approved', 'confirmed']:
                    continue
                # Try 'price' first, then 'amount'
                amount = data.get('price') or data.get('amount') or 0
                
                if user_id and amount:
                    # Convert to number if it's a string
                    if isinstance(amount, str):
                        try:
                            amount = int(amount.replace(',', '').replace('ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¦', ''))
                        except:
                            amount = 0
                    if user_id not in user_spending:
                        user_spending[user_id] = 0
                    user_spending[user_id] += amount
            
            # Get all users
            users_ref = db.collection('users').get()
            
            # Build users list with spending
            users_list = []
            for doc in users_ref:
                user_data = doc.to_dict()
                
                # Skip admin users
                if user_data.get('is_admin', False):
                    continue
                    
                user_id = doc.id
                total_spent = user_spending.get(user_id, 0)
                
                # Try different field names for profile photo
                avatar = user_data.get('photo') or user_data.get('avatar') or user_data.get('profile_photo') or user_data.get('profilePhoto')
                
                users_list.append({
                    'user_id': user_id,
                    'name': user_data.get('full_name') or user_data.get('name') or user_data.get('email', '').split('@')[0],
                    'email': user_data.get('email', ''),
                    'total_spent': total_spent,
                    'avatar': avatar
                })
            
            # Sort by total_spent descending
            users_list.sort(key=lambda x: x.get('total_spent', 0), reverse=True)
            
            # Take top 10
            top_users = users_list[:10]
            return {'success': True, 'data': top_users}
        except Exception as e:
            print(f"Error fetching leaderboard: {e}")
            return {'success': True, 'data': []}
    return {'success': True, 'data': []}


@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')


# Chat API - User sends message to admin
@app.route('/api/chat/send', methods=['POST'])
@login_required
def send_chat_message():
    """User sends a chat message"""
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return {'success': False, 'message': 'Message is required'}, 400
    
    user_id = session.get('user_id')
    user_email = session.get('email', '')
    
    print(f"Chat send - user_id: {user_id}, email: {user_email}, message: {message}")
    
    if db:
        try:
            # Check if user is blocked
            try:
                blocked_doc = db.collection('blocked_users').document(user_id).get()
                if blocked_doc.exists:
                    return {'success': False, 'message': 'You have been blocked from messaging. Contact support.'}, 403
            except:
                pass
            
            # Get user name
            user_name = user_email.split('@')[0] if user_email else 'User'
            try:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_name = user_data.get('full_name', user_name)
            except Exception as e:
                print(f"Error getting user doc: {e}")
            
            # Save message to Firestore
            chat_message = {
                'user_id': user_id,
                'user_name': user_name,
                'user_email': user_email,
                'message': message,
                'sender': 'user',
                'status': 'unread',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('chats').add(chat_message)
            
            return {'success': True}
        except Exception as e:
            print(f"Error sending chat message: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Chat API - Get user's chat messages
@app.route('/api/chat/messages')
@login_required
def get_chat_messages():
    """Get chat messages for current user"""
    user_id = session.get('user_id')
    
    if db:
        try:
            # Get messages sent by user
            messages_ref = db.collection('chats').where('user_id', '==', user_id).order_by('created_at').limit(50).get()
            
            message_list = []
            for doc in messages_ref:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Convert timestamp
                if data.get('created_at'):
                    try:
                        from datetime import datetime
                        import time
                        if hasattr(data['created_at'], 'timestamp'):
                            diff = time.time() - data['created_at'].timestamp()
                            if diff < 60:
                                data['time'] = 'now'
                            elif diff < 3600:
                                data['time'] = f'{int(diff/60)}m ago'
                            elif diff < 86400:
                                data['time'] = f'{int(diff/3600)}h ago'
                            else:
                                data['time'] = 'earlier'
                    except:
                        data['time'] = 'recently'
                
                message_list.append(data)
            
            return {'success': True, 'data': message_list}
        except Exception as e:
            print(f"Error fetching chat messages: {e}")
            # Fallback without ordering
            try:
                messages_ref = db.collection('chats').where('user_id', '==', user_id).limit(50).get()
                message_list = [doc.to_dict() | {'id': doc.id} for doc in messages_ref]
                return {'success': True, 'data': message_list}
            except:
                return {'success': True, 'data': []}
    
    return {'success': True, 'data': []}


# Admin API - Get all chat messages (admin only)
@app.route('/api/admin/chat/messages')
@login_required
def get_all_chat_messages():
    """Get all chat messages for admin"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            messages_ref = db.collection('chats').order_by('created_at', direction=firestore.Query.DESCENDING).limit(100).get()
            
            message_list = []
            for doc in messages_ref:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Convert timestamp
                if data.get('created_at'):
                    try:
                        from datetime import datetime
                        import time
                        if hasattr(data['created_at'], 'timestamp'):
                            diff = time.time() - data['created_at'].timestamp()
                            if diff < 60:
                                data['time'] = 'now'
                            elif diff < 3600:
                                data['time'] = f'{int(diff/60)}m ago'
                            elif diff < 86400:
                                data['time'] = f'{int(diff/3600)}h ago'
                            else:
                                data['time'] = 'earlier'
                    except:
                        data['time'] = 'recently'
                
                message_list.append(data)
            
            return {'success': True, 'data': message_list}
        except Exception as e:
            print(f"Error fetching chat messages: {e}")
            return {'success': True, 'data': []}
    
    return {'success': True, 'data': []}


# API to check if admin is online
@app.route('/api/chat/admin-status')
def get_admin_status():
    """Check if admin is online (presence system)"""
    # For simplicity, we'll track last activity in a "presence" collection
    # In production, you'd use Firebase Realtime Database or WebSockets
    if db:
        try:
            # Check if there's recent admin activity (within last 5 minutes)
            import time
            now = time.time()
            
            # Get admin users who are recently active
            admins_ref = db.collection('users').where('is_admin', '==', True).get()
            
            is_online = False
            for doc in admins_ref:
                data = doc.to_dict()
                last_active = data.get('last_active', 0)
                # Consider online if active within last 5 minutes
                if isinstance(last_active, (int, float)) and (now - last_active) < 300:
                    is_online = True
                    break
            
            return {'success': True, 'is_online': is_online}
        except Exception as e:
            print(f"Error checking admin status: {e}")
            return {'success': True, 'is_online': False}
    
    return {'success': True, 'is_online': False}


# API to get online users (for admin dashboard)
@app.route('/api/admin/online-users')
@login_required
def get_online_users():
    """Get list of online users"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            import time
            now = time.time()
            
            # Get all users who are recently active
            users_ref = db.collection('users').get()
            
            online_users = []
            for doc in users_ref:
                data = doc.to_dict()
                # Skip admins
                if data.get('is_admin', False):
                    continue
                    
                last_active = data.get('last_active', 0)
                # Consider online if active within last 5 minutes
                if isinstance(last_active, (int, float)) and (now - last_active) < 300:
                    online_users.append({
                        'user_id': doc.id,
                        'name': data.get('full_name', data.get('email', 'User').split('@')[0]),
                        'email': data.get('email', '')
                    })
            
            return {'success': True, 'data': online_users}
        except Exception as e:
            print(f"Error getting online users: {e}")
            return {'success': True, 'data': []}
    
    return {'success': True, 'data': []}


# Update user activity (called periodically by client)
@app.route('/api/user/heartbeat', methods=['POST'])
@login_required
def user_heartbeat():
    """Update user's last active time for presence tracking"""
    user_id = session.get('user_id')
    
    if db:
        try:
            import time
            db.collection('users').document(user_id).update({
                'last_active': time.time()
            })
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Admin API - Send reply to chat
@app.route('/api/admin/chat/reply', methods=['POST'])
@login_required
def admin_reply_chat():
    """Admin replies to a chat message"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message', '')
    
    if not message or not user_id:
        return {'success': False, 'message': 'Message and user ID required'}, 400
    
    if db:
        try:
            admin_email = session.get('email', 'admin')
            
            # Save admin reply
            chat_message = {
                'user_id': user_id,
                'user_name': 'Admin',
                'user_email': admin_email,
                'message': message,
                'sender': 'admin',
                'status': 'read',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('chats').add(chat_message)
            
            return {'success': True}
        except Exception as e:
            print(f"Error sending admin reply: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Admin API - Get all users with chat messages
@app.route('/api/admin/chat/users')
@login_required
def get_chat_users():
    """Get all users who have sent messages (for admin messaging center)"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            import time
            
            # Get all chat messages
            all_messages = db.collection('chats').order_by('created_at', direction=firestore.Query.DESCENDING).get()
            
            # Group by user
            users_dict = {}
            for doc in all_messages:
                data = doc.to_dict()
                user_id = data.get('user_id')
                
                if user_id not in users_dict:
                    # Get user info from users collection
                    user_name = data.get('user_name', 'Unknown')
                    user_email = data.get('user_email', '')
                    is_vip = False
                    photo_url = ''
                    
                    try:
                        user_doc = db.collection('users').document(user_id).get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            user_name = user_data.get('full_name', user_name)
                            user_email = user_data.get('email', user_email)
                            is_vip = user_data.get('is_vip', False) or user_data.get('isVIP', False)
                            photo_url = user_data.get('photo_url', '')
                    except:
                        pass
                    
                    users_dict[user_id] = {
                        'user_id': user_id,
                        'user_name': user_name,
                        'user_email': user_email,
                        'is_vip': is_vip,
                        'isVIP': is_vip,
                        'photo_url': photo_url,
                        'last_message': data.get('message', ''),
                        'last_time': '',
                        'unread': 0,
                        'blocked': False
                    }
                    
                    # Check if blocked
                    try:
                        blocked_doc = db.collection('blocked_users').document(user_id).get()
                        if blocked_doc.exists:
                            users_dict[user_id]['blocked'] = True
                    except:
                        pass
                
                # Update last message and time
                if data.get('message'):
                    users_dict[user_id]['last_message'] = data.get('message')
                    
                    # Format time
                    if data.get('created_at'):
                        try:
                            if hasattr(data['created_at'], 'timestamp'):
                                diff = time.time() - data['created_at'].timestamp()
                                if diff < 60:
                                    users_dict[user_id]['last_time'] = 'now'
                                elif diff < 3600:
                                    users_dict[user_id]['last_time'] = f'{int(diff/60)}m ago'
                                elif diff < 86400:
                                    users_dict[user_id]['last_time'] = f'{int(diff/3600)}h ago'
                                else:
                                    users_dict[user_id]['last_time'] = f'{int(diff/86400)}d ago'
                        except:
                            pass
                
                # Count unread (messages from user that aren't read)
                if data.get('sender') == 'user' and data.get('status') != 'read':
                    users_dict[user_id]['unread'] = users_dict[user_id].get('unread', 0) + 1
            
            # Convert to list and sort by last message time
            users_list = list(users_dict.values())
            
            # Sort: unread first, then by time
            users_list.sort(key=lambda x: (-x['unread'], x['last_time']))
            
            # Filter out blocked users
            users_list = [u for u in users_list if not u.get('blocked', False)]
            
            return {'success': True, 'data': users_list}
        except Exception as e:
            print(f"Error fetching chat users: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': True, 'data': []}


# Admin API - Get total unread messages count
@app.route('/api/admin/chat/unread-count')
@login_required
def get_total_unread_count():
    """Get total unread messages count for all users"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            # Get all chat messages
            all_messages = db.collection('chats').get()
            
            total_unread = 0
            users_with_unread = set()
            
            for doc in all_messages:
                data = doc.to_dict()
                # Count unread messages from users
                if data.get('sender') == 'user' and data.get('status') != 'read':
                    user_id = data.get('user_id')
                    # Check if user is not blocked
                    blocked = False
                    try:
                        blocked_doc = db.collection('blocked_users').document(user_id).get()
                        if blocked_doc.exists:
                            blocked = True
                    except:
                        pass
                    
                    if not blocked:
                        total_unread += 1
                        users_with_unread.add(user_id)
            
            return {'success': True, 'total_unread': total_unread, 'users_with_unread': len(users_with_unread)}
        except Exception as e:
            print(f"Error fetching unread count: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': True, 'total_unread': 0, 'users_with_unread': 0}


# Admin API - Get messages for specific user
@app.route('/api/admin/chat/messages/<user_id>')
@login_required
def get_user_messages(user_id):
    """Get all messages for a specific user"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if not user_id or user_id == 'undefined':
        return {'success': True, 'data': []}
    
    if db:
        try:
            import time
            
            # Get messages for this user (without order_by to avoid index issues)
            messages_ref = db.collection('chats').where('user_id', '==', user_id).limit(100).get()
            
            message_list = []
            for doc in messages_ref:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Convert timestamp
                if data.get('created_at'):
                    try:
                        if hasattr(data['created_at'], 'timestamp'):
                            diff = time.time() - data['created_at'].timestamp()
                            if diff < 60:
                                data['time'] = 'now'
                            elif diff < 3600:
                                data['time'] = f'{int(diff/60)}m ago'
                            elif diff < 86400:
                                data['time'] = f'{int(diff/3600)}h ago'
                            else:
                                data['time'] = 'earlier'
                    except:
                        data['time'] = 'recently'
                
                message_list.append(data)
            
            # Sort by created_at manually
            message_list.sort(key=lambda x: x.get('created_at', 0))
            
            return {'success': True, 'data': message_list}
        except Exception as e:
            print(f"Error fetching user messages: {e}")
            return {'success': True, 'data': []}
    
    return {'success': True, 'data': []}


# Admin API - Mark messages as read
@app.route('/api/admin/chat/mark-read', methods=['POST'])
@login_required
def mark_messages_read():
    """Mark all messages from a user as read"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return {'success': False, 'message': 'User ID required'}, 400
    
    if db:
        try:
            # Get all unread messages from this user
            messages_ref = db.collection('chats').where('user_id', '==', user_id).where('status', '==', 'unread').get()
            
            for doc in messages_ref:
                doc.reference.update({'status': 'read'})
            
            return {'success': True}
        except Exception as e:
            print(f"Error marking messages as read: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Admin API - Clear chat history with user
@app.route('/api/admin/chat/clear', methods=['POST'])
@login_required
def clear_user_chat():
    """Clear all chat messages with a user"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return {'success': False, 'message': 'User ID required'}, 400
    
    if db:
        try:
            # Get all messages for this user
            messages_ref = db.collection('chats').where('user_id', '==', user_id).get()
            
            for doc in messages_ref:
                doc.reference.delete()
            
            return {'success': True}
        except Exception as e:
            print(f"Error clearing chat: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Admin API - Block user
@app.route('/api/admin/chat/block', methods=['POST'])
@login_required
def block_user_chat():
    """Block a user from sending messages"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return {'success': False, 'message': 'User ID required'}, 400
    
    if db:
        try:
            # Add to blocked_users collection
            db.collection('blocked_users').document(user_id).set({
                'blocked_at': firestore.SERVER_TIMESTAMP,
                'blocked_by': session.get('email', 'admin')
            })
            
            return {'success': True}
        except Exception as e:
            print(f"Error blocking user: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Admin API - Search users
@app.route('/api/admin/users/search')
@login_required
def search_users():
    """Search users by name or email for admin chat"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return {'success': True, 'data': []}
    
    if db:
        try:
            # Search in users collection
            # We'll do a simple prefix search on email and full_name
            users_ref = db.collection('users').limit(20).get()
            
            results = []
            query_lower = query.lower()
            
            for doc in users_ref:
                data = doc.to_dict()
                full_name = data.get('full_name', '').lower()
                email = data.get('email', '').lower()
                
                if query_lower in full_name or query_lower in email:
                    results.append({
                        'user_id': doc.id,
                        'full_name': data.get('full_name', 'Unknown'),
                        'email': data.get('email', ''),
                        'is_vip': data.get('is_vip', False) or data.get('isVIP', False),
                        'isVIP': data.get('is_vip', False) or data.get('isVIP', False),
                        'photo_url': data.get('photo_url', '')
                    })
            
            return {'success': True, 'data': results[:10]}  # Return max 10 results
        except Exception as e:
            print(f"Error searching users: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': True, 'data': []}


@app.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html')


@app.route('/api/user/notifications')
@login_required
def get_user_notifications():
    """Get user's notifications from various sources"""
    user_id = session.get('user_id')
    
    if db:
        try:
            notifications = []
            seen_notifications = session.get('seen_notifications', [])
            
            # Get user's bookings for notification data (without ordering to avoid index issues)
            bookings = db.collection('bookings').where('user_id', '==', user_id).limit(20).get()
            
            # Convert to list and sort by created_at locally
            bookings_list = [doc.to_dict() | {'id': doc.id} for doc in bookings]
            bookings_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            for data in bookings_list[:10]:
                status = data.get('status', 'pending')
                service = data.get('service', 'Haircut Service')
                price = data.get('price', data.get('amount', 0))
                created_at = data.get('created_at')
                doc_id = data.get('id', '')
                
                # Check if this notification has been seen
                is_seen = doc_id in seen_notifications
                
                # Convert timestamp to readable format
                time_ago = 'recently'
                if created_at:
                    try:
                        from datetime import datetime
                        import time
                        if hasattr(created_at, 'timestamp'):
                            diff = time.time() - created_at.timestamp()
                            if diff < 60:
                                time_ago = 'just now'
                            elif diff < 3600:
                                time_ago = f'{int(diff/60)}m ago'
                            elif diff < 86400:
                                time_ago = f'{int(diff/3600)}h ago'
                            else:
                                time_ago = f'{int(diff/86400)}d ago'
                    except:
                        pass
                
                if status == 'pending':
                    notifications.append({
                        'id': doc_id,
                        'type': 'booking',
                        'icon': 'ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦',
                        'icon_type': 'booking',
                        'title': 'Booking Pending',
                        'message': f'Your appointment for {service} is awaiting confirmation.',
                        'time': time_ago,
                        'unread': not is_seen
                    })
                elif status == 'approved':
                    notifications.append({
                        'id': doc_id,
                        'type': 'booking',
                        'icon': 'ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦',
                        'icon_type': 'success',
                        'title': 'Booking Approved',
                        'message': f'Your appointment for {service} has been approved!',
                        'time': time_ago,
                        'unread': not is_seen
                    })
                elif status == 'confirmed':
                    notifications.append({
                        'id': doc_id,
                        'type': 'booking',
                        'icon': 'ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦',
                        'icon_type': 'booking',
                        'title': 'Booking Confirmed',
                        'message': f'Your appointment for {service} has been confirmed.',
                        'time': time_ago,
                        'unread': False
                    })
            
            # Get user profile for VIP status
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                is_vip = user_data.get('isVIP', False)
                
                if is_vip:
                    notifications.append({
                        'id': 'vip_status',
                        'type': 'vip',
                        'icon': 'ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“',
                        'icon_type': 'vip',
                        'title': 'VIP Status Active',
                        'message': 'You are a VIP member! Enjoy priority cutting and exclusive benefits.',
                        'time': 'active',
                        'unread': False
                    })
            
            return {'success': True, 'data': notifications}
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return {'success': True, 'data': []}
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/user/notifications/mark-read', methods=['POST'])
@login_required
def mark_notification_read():
    """Mark a notification as read"""
    data = request.get_json()
    notification_id = data.get('notification_id')
    
    if not notification_id:
        return {'success': False, 'message': 'Notification ID required'}, 400
    
    # Store in session (for simplicity - in production, store in DB)
    seen_notifications = session.get('seen_notifications', [])
    if notification_id not in seen_notifications:
        seen_notifications.append(notification_id)
        session['seen_notifications'] = seen_notifications
    
    return {'success': True}


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/admin/approvals')
@login_required
def admin_approvals():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('approvals.html')


@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Get all bookings from database (not just pending)
    bookings = []
    if db:
        try:
            # Get all bookings
            all_bookings = db.collection('bookings').limit(100).get()
            for doc in all_bookings:
                booking = doc.to_dict()
                booking['id'] = doc.id
                # Show pending and pending_approval bookings
                if booking.get('status') in ['pending', 'pending_approval']:
                    bookings.append(booking)
        except Exception as e:
            print(f"Error loading bookings: {e}")
    
    return render_template('admin-bookings.html', bookings=bookings)


@app.route('/api/admin/approve-booking', methods=['POST'])
@login_required
def approve_booking():
    """Update booking status - confirm (move to approvals) or finalize"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    booking_id = data.get('bookingId')
    action = data.get('action', 'confirm')
    
    if not booking_id:
        return jsonify({'success': False, 'message': 'No booking ID provided'}), 400
    
    if db:
        try:
            # Get the booking
            booking_doc = db.collection('bookings').document(booking_id).get()
            if not booking_doc.exists:
                return jsonify({'success': False, 'message': 'Booking not found'}), 404
            
            booking_data = booking_doc.to_dict()
            current_status = booking_data.get('status')
            
            if action == 'confirm':
                # Move to approvals - add to approvals collection
                approval_data = {
                    'user_id': booking_data.get('user_id'),
                    'user_email': booking_data.get('user_email'),
                    'user_name': booking_data.get('user_name'),
                    'type': 'booking',
                    'service': booking_data.get('service') or booking_data.get('requests'),
                    'amount': booking_data.get('price'),
                    'booking_id': booking_id,
                    'status': 'pending',
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                db.collection('approvals').add(approval_data)
                
                # Update booking status to 'pending_approval'
                db.collection('bookings').document(booking_id).update({
                    'status': 'pending_approval'
                })
                
                return jsonify({'success': True, 'message': 'Booking moved to approvals'})
            
            elif action == 'approve':
                # Final approval - mark as confirmed
                db.collection('bookings').document(booking_id).update({
                    'status': 'confirmed'
                })
                
                # Remove from approvals if exists
                approvals = db.collection('approvals').where('booking_id', '==', booking_id).get()
                for doc in approvals:
                    doc.reference.delete()
                
                return jsonify({'success': True, 'message': 'Booking confirmed successfully'})
            
            elif action == 'cancel' or action == 'cancelled':
                # Cancel the booking
                db.collection('bookings').document(booking_id).update({
                    'status': 'cancelled'
                })
                
                # Remove from approvals if exists
                approvals = db.collection('approvals').where('booking_id', '==', booking_id).get()
                for doc in approvals:
                    doc.reference.delete()
                
                return jsonify({'success': True, 'message': 'Booking cancelled'})
            
            else:
                return jsonify({'success': False, 'message': 'Invalid action'}), 400
                
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Database not available'}), 500


@app.route('/admin/ledger')
@login_required
def admin_ledger():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Get completed transactions from ledger
    ledger = []
    if db:
        try:
            all_ledger = db.collection('ledger').order_by('created_at', direction=firestore.Query.DESCENDING).get()
            for doc in all_ledger:
                entry = doc.to_dict()
                entry['id'] = doc.id
                ledger.append(entry)
        except Exception as e:
            print(f"Error loading ledger: {e}")
    
    return render_template('ledger.html', ledger=ledger)


@app.route('/api/admin/ledger')
@login_required
def get_ledger_api():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    ledger = []
    if db:
        try:
            all_ledger = db.collection('ledger').order_by('created_at', direction=firestore.Query.DESCENDING).limit(50).get()
            for doc in all_ledger:
                data = doc.to_dict()
                data['id'] = doc.id
                ledger.append(data)
            return jsonify({'success': True, 'data': ledger})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Database not available'}), 500


# Admin API - Add expense
@app.route('/api/admin/ledger/expense', methods=['POST'])
@login_required
def add_ledger_expense():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    amount = data.get('amount')
    description = data.get('description')
    
    if not amount or not description:
        return jsonify({'success': False, 'message': 'Amount and description required'}), 400
    
    if db:
        try:
            expense = {
                'amount': float(amount),
                'label': description,
                'type': 'expense',
                'created_at': firestore.SERVER_TIMESTAMP,
                'created_by': session.get('email')
            }
            db.collection('ledger').add(expense)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Database not available'}), 500


# Admin API - Delete ledger transaction
@app.route('/api/admin/ledger/<transaction_id>', methods=['DELETE'])
@login_required
def delete_ledger_transaction(transaction_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    if db:
        try:
            db.collection('ledger').document(transaction_id).delete()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Database not available'}), 500


@app.route('/admin/analytics')
@login_required
def admin_analytics():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('analytics.html')


@app.route('/admin')
@login_required
def admin():
    # Check if user is admin
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('admin.html')


@app.route('/admin-login')
def admin_login():
    return render_template('admin-login.html')


# API Routes for Authentication
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    try:
        # Sign in with Firebase Auth
        user = auth.get_user_by_email(email)
        
        # In production, verify password using Firebase Auth
        # For demo, we'll create a session
        session['user_id'] = user.uid
        session['email'] = user.email
        
        # Get user role from Firestore
        if db:
            user_doc = db.collection('users').document(user.uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                session['is_admin'] = user_data.get('is_admin', False)
                session['user_name'] = user_data.get('full_name', 'User')
        
        return {'success': True, 'message': 'Login successful'}
    except auth.UserNotFoundError:
        return {'success': False, 'message': 'User not found'}, 401
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone = data.get('phone')
    referral_code = normalize_referral_code(data.get('referral_code', ''))
    
    try:
        # Create user in Firebase Auth
        user = auth.create_user(
            email=email,
            password=password,
            display_name=full_name
        )
        
        # Store user data in Firestore
        if db:
            user_data = {
                'uid': user.uid,
                'email': email,
                'full_name': full_name,
                'phone': phone,
                'referral_code': 'CELEB-' + user.uid[:4].upper(),
                'is_admin': False,
                'is_vip': False,
                'total_spent': 0,
                'referral_count': 0,
                'created_at': firestore.SERVER_TIMESTAMP
            }

            if referral_code:
                try:
                    referrers = db.collection('users').where('referral_code', '==', referral_code).limit(1).get()
                    if referrers:
                        referrer_id = referrers[0].id
                        user_data['used_referral_code'] = referral_code
                        db.collection('users').document(referrer_id).update({
                            'referral_count': firestore.Increment(1)
                        })
                    else:
                        print(f"Referral code not found: {referral_code}")
                except Exception as e:
                    print(f"Error applying referral on api signup: {e}")

            db.collection('users').document(user.uid).set(user_data)
        
        # Create session
        session['user_id'] = user.uid
        session['email'] = user.email
        session['user_name'] = full_name
        session['is_admin'] = False
        
        return {'success': True, 'message': 'Account created successfully'}
    except auth.EmailAlreadyExistsError:
        return {'success': False, 'message': 'Email already exists'}, 400
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500


@app.route('/api/logout')
def api_logout():
    session.clear()
    return {'success': True, 'message': 'Logged out successfully'}


@app.route('/logout')
def logout():
    """Logout route that redirects to home page"""
    session.clear()
    return redirect(url_for('index'))


# API Routes for Data
@app.route('/api/user/profile')
@login_required
def get_user_profile():
    user_id = session.get('user_id')
    
    if db:
        try:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                return {'success': True, 'data': user_doc.to_dict()}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'User not found'}, 404


@app.route('/api/user/bookings')
@login_required
def get_user_bookings():
    user_id = session.get('user_id')
    
    if db:
        try:
            bookings = db.collection('bookings').where('user_id', '==', user_id).get()
            booking_list = [doc.to_dict() for doc in bookings]
            return {'success': True, 'data': booking_list}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'No bookings'}, 404


@app.route('/api/user/transactions')
@login_required
def get_user_transactions():
    user_id = session.get('user_id')
    
    if db:
        try:
            transactions = db.collection('transactions').where('user_id', '==', user_id).get()
            transaction_list = [doc.to_dict() for doc in transactions]
            return {'success': True, 'data': transaction_list}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'No transactions'}, 404


# Admin API Routes
@app.route('/api/admin/users')
@login_required
def get_all_users():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            users = db.collection('users').get()
            user_list = []
            for doc in users:
                data = doc.to_dict()
                data['user_id'] = doc.id
                user_list.append(data)
            return {'success': True, 'data': user_list}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/users/<user_id>/details')
@login_required
def get_user_details(user_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            # Get user
            user_doc = db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return {'success': False, 'message': 'User not found'}, 404
            
            user_data = user_doc.to_dict()
            
            # Get bookings
            bookings = db.collection('bookings').where('user_id', '==', user_id).get()
            bookings_list = []
            total_spent = 0
            for doc in bookings:
                data = doc.to_dict()
                data['id'] = doc.id
                if data.get('status') in ['confirmed', 'approved']:
                    total_spent += data.get('price', 0)
                bookings_list.append(data)
            
            # Sort bookings by date
            bookings_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Get referrals
            referrals = db.collection('referrals').where('referrer_id', '==', user_id).get()
            referral_count = len(referrals)
            
            return {
                'success': True,
                'data': {
                    'total_spent': total_spent,
                    'booking_count': len(bookings_list),
                    'referral_count': referral_count,
                    'bookings': bookings_list
                }
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            db.collection('users').document(user_id).delete()
            return {'success': True, 'message': 'User deleted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/analytics')
@login_required
def get_analytics():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            # Get total users
            users = db.collection('users').get()
            total_users = len(users)
            
            # Get total revenue
            transactions = db.collection('transactions').get()
            total_revenue = sum(t.get('amount', 0) for t in [doc.to_dict() for doc in transactions] if t.get('type') == 'income')
            
            # Get VIP users
            vip_users = len([u for u in db.collection('users').where('is_vip', '==', True).get()])
            
            return {
                'success': True,
                'data': {
                    'total_users': total_users,
                    'total_revenue': total_revenue,
                    'active_vips': vip_users
                }
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/pending-approvals')
@login_required
def get_pending_approvals():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            # Get all approvals and filter manually (faster than complex queries)
            all_approvals = db.collection('approvals').limit(50).get()
            approval_list = []
            for doc in all_approvals:
                data = doc.to_dict()
                if data.get('status') == 'pending':
                    data['id'] = doc.id
                    approval_list.append(data)
                # Stop after getting 20 pending approvals
                if len(approval_list) >= 20:
                    break
            return {'success': True, 'data': approval_list}
        except Exception as e:
            print(f"Error fetching approvals: {e}")
            return {'success': False, 'data': [], 'message': str(e)}, 200  # Return empty instead of error
    
    return {'success': True, 'data': []}


@app.route('/api/admin/approve', methods=['POST'])
@login_required
def approve_request():
    """Final confirmation from approvals - adds to ledger and updates user spending"""
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    request_id = data.get('requestId')
    request_type = data.get('requestType')
    
    if not request_id:
        return {'success': False, 'message': 'No request ID provided'}, 400
    
    if db:
        try:
            # Get the approval document
            doc_ref = db.collection('approvals').document(request_id)
            approval_doc = doc_ref.get()
            
            if not approval_doc.exists:
                return {'success': False, 'message': 'Approval not found'}, 404
            
            approval_data = approval_doc.to_dict()
            amount = approval_data.get('amount', 0)
            user_id_from_approval = approval_data.get('user_id')
            
            # Update approval status to confirmed
            doc_ref.update({
                'status': 'confirmed',
                'confirmedAt': datetime.now().isoformat(),
                'confirmedBy': session.get('email')
            })
            
            # Add to ledger
            ledger_entry = {
                'user_id': user_id_from_approval,
                'user_email': approval_data.get('user_email'),
                'user_name': approval_data.get('user_name'),
                'type': request_type,
                'service': approval_data.get('service'),
                'amount': amount,
                'status': 'confirmed',
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('ledger').add(ledger_entry)
            
            # If VIP request, update user VIP status
            if request_type == 'vip' and user_id_from_approval:
                try:
                    db.collection('users').document(user_id_from_approval).update({
                        'is_vip': True,
                        'vipSince': datetime.now().isoformat(),
                        'vipExpires': datetime.now().replace(month=datetime.now().month + 1).isoformat()
                    })
                except Exception as e:
                    print(f"Error updating VIP: {e}")
            
            # Update user's total_spent when booking is confirmed
            if request_type == 'booking' and user_id_from_approval and amount > 0:
                try:
                    # Convert amount to number if it's a string
                    if isinstance(amount, str):
                        try:
                            amount = int(amount.replace(',', '').replace('ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¦', ''))
                        except:
                            amount = 0
                    user_doc = db.collection('users').document(user_id_from_approval).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        current_spent = user_data.get('total_spent', 0)
                        # Convert current_spent to number if it's a string
                        if isinstance(current_spent, str):
                            try:
                                current_spent = int(current_spent.replace(',', '').replace('ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¦', ''))
                            except:
                                current_spent = 0
                        db.collection('users').document(user_id_from_approval).update({
                            'total_spent': current_spent + amount
                        })
                except Exception as e:
                    print(f"Error updating spending: {e}")
            
            return {'success': True, 'message': 'Request confirmed and added to ledger'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/decline', methods=['POST'])
@login_required
def decline_request():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    request_id = data.get('requestId')
    reason = data.get('reason', 'Not specified')
    
    if not request_id:
        return {'success': False, 'message': 'No request ID provided'}, 400
    
    if db:
        try:
            # Update approval status to declined
            doc_ref = db.collection('approvals').document(request_id)
            doc_ref.update({
                'status': 'declined',
                'declinedAt': datetime.now().isoformat(),
                'declinedBy': session.get('email'),
                'declineReason': reason
            })
            
            return {'success': True, 'message': 'Request declined'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Additional Admin Routes (referenced in admin.html but not implemented)
@app.route('/admin/referrals')
@login_required
def admin_referrals():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('admin-referrals.html')


# Admin API - Get all referrals
@app.route('/api/admin/referrals')
@login_required
def get_all_referrals():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            # Get all users with their referral data
            users_ref = db.collection('users').get()
            
            referrals = []
            for user_doc in users_ref:
                user_data = user_doc.to_dict()
                
                # Check if this user was referred (has used_referral_code)
                used_code = normalize_referral_code(user_data.get('used_referral_code', ''))
                if used_code:
                    # Find the referrer
                    referrers = db.collection('users').where('referral_code', '==', used_code).get()
                    referrer_name = 'Unknown'
                    referrer_code = used_code
                    referrer_photo = ''
                    referral_count = 0

                    for referrer in referrers:
                        ref_data = referrer.to_dict()
                        referrer_name = ref_data.get('full_name', 'Unknown')
                        referrer_photo = ref_data.get('photo_url', '')
                        referral_count = ref_data.get('referral_count', 0)
                        break

                    # Determine status - check referral_status field first, then spending fallback
                    status = user_data.get('referral_status', '')
                    total_spent = user_data.get('total_spent', 0)
                    if isinstance(total_spent, str):
                        try:
                            total_spent = float(''.join(ch for ch in total_spent if ch.isdigit() or ch in ['.', '-']))
                        except Exception:
                            total_spent = 0
                    if not status:
                        if total_spent > 0:
                            status = 'successful'
                        else:
                            status = 'pending'
                    
                    # Get last claimed reward
                    last_claimed = user_data.get('last_claimed_reward', None)
                    
                    # Get creation timestamp
                    created_at = 0
                    if user_data.get('created_at'):
                        try:
                            created_at = user_data['created_at'].timestamp()
                        except:
                            pass
                    
                    referrals.append({
                        'id': user_doc.id,
                        'referrer_id': referrers[0].id if referrers else '',
                        'referrer_name': referrer_name,
                        'referrer_code': referrer_code,
                        'referrer_photo': referrer_photo,
                        'referred_id': user_doc.id,
                        'referred_name': user_data.get('full_name', 'Unknown Friend'),
                        'status': status,
                        'referral_count': referral_count if referrers else 0,
                        'last_claimed': last_claimed,
                        'created_at': created_at
                    })
            
            print(f"Found {len(referrals)} referrals")
            for ref in referrals:
                print(f"  - {ref['referrer_name']} -> {ref['referred_name']} ({ref['status']})")
            
            # Sort by date (newest first)
            referrals.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            
            return {'success': True, 'data': referrals}
        except Exception as e:
            print(f"Error fetching referrals: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': True, 'data': []}


# Admin API - Verify referral
@app.route('/api/admin/referrals/verify', methods=['POST'])
@login_required
def verify_referral():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    referral_id = data.get('referral_id')
    
    if not referral_id:
        return {'success': False, 'message': 'Referral ID required'}, 400
    
    if db:
        try:
            # Mark referral as verified/successful
            db.collection('users').document(referral_id).update({
                'referral_verified': True,
                'referral_verified_at': firestore.SERVER_TIMESTAMP,
                'referral_status': 'successful'
            })
            
            return {'success': True}
        except Exception as e:
            print(f"Error verifying referral: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Admin API - Grant reward and reset streak
@app.route('/api/admin/referrals/reward', methods=['POST'])
@login_required
def grant_referral_reward():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    referral_id = data.get('referral_id')
    reward_type = data.get('reward_type', '30off')  # '30off' or 'freecut'
    
    if not referral_id:
        return {'success': False, 'message': 'Referral ID required'}, 400
    
    if db:
        try:
            # Update user's reward status
            reward_value = '30% OFF' if reward_type == '30off' else 'FREE CUT'
            
            # Get current user data to find referrer
            referred_user = db.collection('users').document(referral_id).get()
            if not referred_user.exists:
                return {'success': False, 'message': 'User not found'}, 404
            
            user_data = referred_user.to_dict()
            used_code = normalize_referral_code(user_data.get('used_referral_code', ''))
            
            # Update the referred user (the one who made the purchase)
            db.collection('users').document(referral_id).update({
                'last_claimed_reward': reward_type,
                'reward_claimed_at': firestore.SERVER_TIMESTAMP,
                'pending_reward_claim': False,
                'referral_verified': True,
                'referral_status': 'successful',
                'total_referrals': firestore.Increment(1)
            })
            
            # If there's a referrer, reset their streak
            if used_code:
                referrers = db.collection('users').where('referral_code', '==', used_code).get()
                for referrer in referrers:
                    # Reset the referrer's streak to 0
                    db.collection('users').document(referrer.id).update({
                        'referral_streak': 0,
                        'last_reward_claimed': reward_type,
                        'last_reward_claimed_at': firestore.SERVER_TIMESTAMP
                    })
                    print(f"Reset streak for referrer {referrer.id}")
            
            return {'success': True, 'message': f'{reward_value} reward granted. Streak reset!'}
        except Exception as e:
            print(f"Error granting reward: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# User API - Get user's referral history
@app.route('/api/user/referrals')
@login_required
def get_user_referrals():
    """Get user's referral history - who they referred and status"""
    user_id = session.get('user_id')
    
    if not user_id:
        return {'success': False, 'message': 'Not logged in'}, 401
    
    if db:
        try:
            # Get current user's referral code
            user_doc = db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return {'success': False, 'message': 'User not found'}, 404
            
            user_data = user_doc.to_dict()
            my_referral_code = normalize_referral_code(user_data.get('referral_code', ''))
            
            # Find users who used this code (normalize stored values to handle old mixed-case data)
            referrals = []
            if my_referral_code:
                all_users = db.collection('users').get()

                for ref_user in all_users:
                    ref_data = ref_user.to_dict()
                    used_code = normalize_referral_code(ref_data.get('used_referral_code', ''))
                    if used_code != my_referral_code:
                        continue
                    
                    # Get status
                    status = ref_data.get('referral_status', 'pending')
                    if ref_data.get('total_spent', 0) > 0 and status != 'successful':
                        status = 'successful'
                    
                    # Get claimed reward
                    claimed = ref_data.get('last_claimed_reward', None)
                    
                    referrals.append({
                        'id': ref_user.id,
                        'name': ref_data.get('full_name', 'Unknown'),
                        'email': ref_data.get('email', ''),
                        'status': status,
                        'claimed': claimed,
                        'referred_at': ref_data.get('created_at', None)
                    })
            
            return {'success': True, 'data': referrals}
        except Exception as e:
            print(f"Error fetching user referrals: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': True, 'data': []}


# Admin API - Delete referral
@app.route('/api/admin/referrals/delete', methods=['POST'])
@login_required
def delete_referral():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    referral_id = data.get('referral_id')
    
    if not referral_id:
        return {'success': False, 'message': 'Referral ID required'}, 400
    
    if db:
        try:
            # Clear referral data for the user
            db.collection('users').document(referral_id).update({
                'used_referral_code': firestore.DELETE_FIELD,
                'referral_verified': firestore.DELETE_FIELD
            })
            
            return {'success': True}
        except Exception as e:
            print(f"Error deleting referral: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/admin/users')
@login_required
def admin_users():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Get all users from database
    users = []
    if db:
        try:
            all_users = db.collection('users').get()
            for doc in all_users:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                users.append(user_data)
        except Exception as e:
            print(f"Error loading users: {e}")
    
    return render_template('admin-users.html', users=users)


@app.route('/admin/vips')
@login_required
def admin_vips():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Get all VIP users - check both is_vip and isVIP for backwards compatibility
    vip_users = []
    total_spending = 0
    if db:
        try:
            # First try is_vip (new format)
            vips = db.collection('users').where('is_vip', '==', True).get()
            for doc in vips:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                # Add to total spending
                spent = user_data.get('total_spent', 0)
                if isinstance(spent, str):
                    try:
                        spent = int(spent.replace(',', '').replace('ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¦', ''))
                    except:
                        spent = 0
                total_spending += spent
                vip_users.append(user_data)
            
            # Also check isVIP (old format) for backwards compatibility
            vips_old = db.collection('users').where('isVIP', '==', True).get()
            for doc in vips_old:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                # Only add if not already in list
                if not any(u.get('id') == doc.id for u in vip_users):
                    # Add to total spending
                    spent = user_data.get('total_spent', 0)
                    if isinstance(spent, str):
                        try:
                            spent = int(spent.replace(',', '').replace('ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¦', ''))
                        except:
                            spent = 0
                    total_spending += spent
                    vip_users.append(user_data)
        except Exception as e:
            print(f"Error loading VIPs: {e}")
    
    return render_template('admin-vips.html', vip_users=vip_users, total_spending=total_spending)


# Admin VIP API Routes
@app.route('/api/admin/vips')
@login_required
def get_all_vips():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            vip_users = []
            
            # Get all users and filter for VIPs (check both is_vip and isVIP)
            users = db.collection('users').get()
            for doc in users:
                user_data = doc.to_dict()
                is_vip = user_data.get('is_vip', False) or user_data.get('isVIP', False)
                
                if is_vip:
                    user_data['user_id'] = doc.id
                    user_data['full_name'] = user_data.get('full_name', user_data.get('email', 'Unknown').split('@')[0])
                    
                    # Calculate time remaining
                    vip_expires = user_data.get('vip_expires')
                    if vip_expires:
                        try:
                            from datetime import datetime
                            exp_date = datetime.fromisoformat(vip_expires.replace('Z', '+00:00'))
                            now = datetime.now(exp_date.tzinfo)
                            remaining = exp_date - now
                            days = remaining.days
                            hours = remaining.seconds // 3600
                            user_data['time_remaining'] = f"{days}d : {hours}h"
                            user_data['expiring_soon'] = days < 1
                        except:
                            user_data['time_remaining'] = 'N/A'
                            user_data['expiring_soon'] = False
                    else:
                        user_data['time_remaining'] = 'N/A'
                        user_data['expiring_soon'] = False
                    
                    # VIP level
                    user_data['vip_level'] = user_data.get('vip_level', 'Member')
                    
                    # Cuts used
                    user_data['cuts_used'] = user_data.get('priority_cuts_used', 0)
                    
                    # Lining active
                    user_data['lining_active'] = user_data.get('lining_unlimited', True)
                    
                    vip_users.append(user_data)
            
            return {'success': True, 'data': vip_users}
        except Exception as e:
            print(f"Error loading VIPs: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/vips/order', methods=['POST'])
@login_required
def save_vip_order():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    order = data.get('order', [])
    
    if db:
        try:
            # Save order to settings
            db.collection('settings').document('vip_queue').set({'order': order}, merge=True)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/vips/<user_id>/cut', methods=['POST'])
@login_required
def toggle_vip_cut(user_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    cut_number = data.get('cut_number', 1)
    
    if db:
        try:
            user_doc = db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return {'success': False, 'message': 'User not found'}, 404
            
            user_data = user_doc.to_dict()
            cuts_used = user_data.get('priority_cuts_used', 0)
            
            # Toggle cut usage
            if cuts_used >= cut_number:
                # Unmark (decrease)
                new_cuts = max(0, cuts_used - 1)
            else:
                # Mark as used
                new_cuts = cut_number
            
            db.collection('users').document(user_id).update({
                'priority_cuts_used': new_cuts,
                f'cut_{cut_number}_at': firestore.SERVER_TIMESTAMP if new_cuts >= cut_number else None
            })
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/vips/<user_id>/gift', methods=['POST'])
@login_required
def gift_vip_days(user_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    days = data.get('days', 0)
    
    if days <= 0:
        return {'success': False, 'message': 'Invalid days'}, 400
    
    if db:
        try:
            from datetime import datetime, timedelta
            
            user_doc = db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return {'success': False, 'message': 'User not found'}, 404
            
            user_data = user_doc.to_dict()
            vip_expires = user_data.get('vip_expires')
            
            # Add days to current expiry
            if vip_expires:
                try:
                    exp_date = datetime.fromisoformat(vip_expires.replace('Z', '+00:00'))
                    new_exp = exp_date + timedelta(days=days)
                except:
                    new_exp = datetime.now() + timedelta(days=30)
            else:
                new_exp = datetime.now() + timedelta(days=30)
            
            db.collection('users').document(user_id).update({
                'vip_expires': new_exp.isoformat(),
                'bonus_days_added': firestore.SERVER_TIMESTAMP
            })
            
            return {'success': True, 'message': f'Added {days} days'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/api/admin/vips/<user_id>/revoke', methods=['POST'])
@login_required
def revoke_vip(user_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            db.collection('users').document(user_id).update({
                'is_vip': False,
                'vip_revoked_at': firestore.SERVER_TIMESTAMP
            })
            
            return {'success': True, 'message': 'VIP status revoked'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Error'}, 500


@app.route('/admin/chat')
@login_required
def admin_chat():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('admin-messages.html')


@app.route('/admin/broadcast')
@login_required
def admin_broadcast():
    if not session.get('is_admin'):
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('admin-broadcast.html')


@app.route('/api/admin/broadcast', methods=['POST'])
@login_required
def broadcast_message():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    image = data.get('image', '')
    
    if not title or not content:
        return {'success': False, 'message': 'Title and content required'}, 400
    
    if db:
        try:
            # Store broadcast in database
            broadcast_data = {
                'title': title,
                'content': content,
                'image': image,
                'sentBy': session.get('email'),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'status': 'active'
            }
            db.collection('broadcasts').add(broadcast_data)
            
            return {'success': True, 'message': 'Broadcast sent successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/broadcasts')
@login_required
def get_broadcasts():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            broadcasts = db.collection('broadcasts').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(50).get()
            broadcast_list = []
            for doc in broadcasts:
                data = doc.to_dict()
                data['id'] = doc.id
                broadcast_list.append(data)
            return {'success': True, 'data': broadcast_list}
        except Exception as e:
            print(f"Error fetching broadcasts: {e}")
            return {'success': True, 'data': []}
    
    return {'success': True, 'data': []}


# Client API to get broadcasts
@app.route('/api/broadcasts')
@login_required
def get_client_broadcasts():
    """Get active broadcasts for client dashboard"""
    if db:
        try:
            broadcasts = db.collection('broadcasts').where('status', '==', 'active').limit(10).get()
            broadcast_list = []
            for doc in broadcasts:
                data = doc.to_dict()
                data['id'] = doc.id
                broadcast_list.append(data)
            # Sort by createdAt descending in memory
            broadcast_list.sort(key=lambda x: x.get('createdAt', 0), reverse=True)
            return {'success': True, 'data': broadcast_list}
        except Exception as e:
            print(f"Error fetching broadcasts: {e}")
            return {'success': True, 'data': []}
    
    return {'success': True, 'data': []}


@app.route('/api/admin/broadcast/<broadcast_id>', methods=['DELETE'])
@login_required
def delete_broadcast(broadcast_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            db.collection('broadcasts').document(broadcast_id).delete()
            return {'success': True, 'message': 'Broadcast deleted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/broadcast/repost', methods=['POST'])
@login_required
def repost_broadcast():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    broadcast_id = data.get('id')
    
    if not broadcast_id:
        return {'success': False, 'message': 'Broadcast ID required'}, 400
    
    if db:
        try:
            # Get the original broadcast
            doc = db.collection('broadcasts').document(broadcast_id).get()
            if not doc.exists:
                return {'success': False, 'message': 'Broadcast not found'}, 404
            
            broadcast_data = doc.to_dict()
            
            # Create a new copy with updated timestamp
            new_broadcast = {
                'title': broadcast_data.get('title'),
                'content': broadcast_data.get('content'),
                'image': broadcast_data.get('image', ''),
                'sentBy': session.get('email'),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'status': 'active',
                'repostedFrom': broadcast_id
            }
            db.collection('broadcasts').add(new_broadcast)
            
            return {'success': True, 'message': 'Broadcast reposted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Service Updates Routes
@app.route('/admin/service-updates')
@login_required
def admin_service_updates():
    if not session.get('is_admin'):
        return redirect('/')
    return render_template('admin-service-updates.html')


@app.route('/api/admin/service-updates', methods=['GET'])
@login_required
def get_service_updates():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            updates = db.collection('service_updates').order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
            updates_list = []
            for doc in updates:
                data = doc.to_dict()
                data['id'] = doc.id
                # Convert timestamp to unix
                if data.get('createdAt'):
                    data['created_at'] = int(data['createdAt'].timestamp())
                updates_list.append(data)
            return {'success': True, 'data': updates_list}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/service-updates', methods=['POST'])
@login_required
def create_service_update():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    update_type = data.get('type', 'other')
    title = data.get('title', '')
    message = data.get('message', '')
    priority = data.get('priority', 'low')
    
    if not title or not message:
        return {'success': False, 'message': 'Title and message required'}, 400
    
    if db:
        try:
            new_update = {
                'type': update_type,
                'title': title,
                'message': message,
                'priority': priority,
                'sentBy': session.get('email'),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'status': 'active'
            }
            db.collection('service_updates').add(new_update)
            return {'success': True, 'message': 'Service update posted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/service-updates/delete', methods=['POST'])
@login_required
def delete_service_update():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    update_id = data.get('update_id')
    
    if not update_id:
        return {'success': False, 'message': 'Update ID required'}, 400
    
    if db:
        try:
            db.collection('service_updates').document(update_id).delete()
            return {'success': True, 'message': 'Service update deleted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


# Services Manager Routes
@app.route('/admin/services')
@login_required
def admin_services():
    if not session.get('is_admin'):
        return redirect('/')
    return render_template('admin-services.html')


@app.route('/api/admin/services', methods=['GET'])
@login_required
def get_services():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            services = db.collection('services').stream()
            services_list = []
            for doc in services:
                data = doc.to_dict()
                data['id'] = doc.id
                services_list.append(data)
            return {'success': True, 'data': services_list}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/services', methods=['GET'])
def get_services_public():
    """Public endpoint for users to get available services"""
    if db:
        try:
            services = db.collection('services').stream()
            services_list = []
            for doc in services:
                data = doc.to_dict()
                data['id'] = doc.id
                # Only include visible services
                if data.get('visible', True):
                    services_list.append(data)
            return {'success': True, 'data': services_list}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/services', methods=['POST'])
@login_required
def create_service():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    price = data.get('price', 0)
    
    if not name or price <= 0:
        return {'success': False, 'message': 'Valid name and price required'}, 400
    
    if db:
        try:
            new_service = {
                'name': name,
                'price': price,
                'visible': True,
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('services').add(new_service)
            return {'success': True, 'message': 'Service created'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/services/<service_id>', methods=['PUT'])
@login_required
def update_service(service_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    price = data.get('price', 0)
    
    if not name or price <= 0:
        return {'success': False, 'message': 'Valid name and price required'}, 400
    
    if db:
        try:
            db.collection('services').document(service_id).update({
                'name': name,
                'price': price
            })
            return {'success': True, 'message': 'Service updated'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/services/<service_id>', methods=['DELETE'])
@login_required
def delete_service(service_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            db.collection('services').document(service_id).delete()
            return {'success': True, 'message': 'Service deleted'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/services/<service_id>/visibility', methods=['POST'])
@login_required
def toggle_service_visibility(service_id):
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    visible = data.get('visible', True)
    
    if db:
        try:
            db.collection('services').document(service_id).update({
                'visible': visible
            })
            return {'success': True, 'message': 'Visibility updated'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/vip-price', methods=['GET'])
@login_required
def get_vip_price():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    if db:
        try:
            doc = db.collection('settings').document('vip').get()
            if doc.exists:
                return {'success': True, 'price': doc.to_dict().get('monthly_price', 2500)}
            return {'success': True, 'price': 2500}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


@app.route('/api/admin/vip-price', methods=['POST'])
@login_required
def update_vip_price():
    if not session.get('is_admin'):
        return {'success': False, 'message': 'Access denied'}, 403
    
    data = request.get_json()
    price = data.get('price', 0)
    
    if price <= 0:
        return {'success': False, 'message': 'Valid price required'}, 400
    
    if db:
        try:
            db.collection('settings').document('vip').set({
                'monthly_price': price
            }, merge=True)
            return {'success': True, 'message': 'VIP price updated'}
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
    
    return {'success': False, 'message': 'Database not available'}, 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
