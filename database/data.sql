-- Campus X Mart: sample data for campus_x_mart_corrected_schema.sql
-- Run this only after the corrected schema has been loaded into an empty database.
-- The password hashes are placeholders. Replace them with bcrypt/Argon2 hashes
-- created by the registration API before using the app in production.

INSERT INTO users
    (username, full_name, email, phone, password_hash, profile_image_url,
     email_verified, phone_verified)
VALUES
    ('rahim',  'Rahim Ahmed',  'rahim@example.com',  '01711111111', '$2b$12$placeholder_hash_for_rahim',  NULL, TRUE, TRUE),
    ('karim',  'Karim Hasan',  'karim@example.com',  '01822222222', '$2b$12$placeholder_hash_for_karim',  NULL, TRUE, TRUE),
    ('sakib',  'Sakib Khan',   'sakib@example.com',  '01933333333', '$2b$12$placeholder_hash_for_sakib',  NULL, TRUE, TRUE),
    ('nusrat', 'Nusrat Jahan', 'nusrat@example.com', '01644444444', '$2b$12$placeholder_hash_for_nusrat', NULL, TRUE, TRUE),
    ('tanvir', 'Tanvir Hossain','tanvir@example.com','01555555555', '$2b$12$placeholder_hash_for_tanvir', NULL, TRUE, TRUE),
    ('admin',  'Campus Admin', 'admin@example.com',  '01300000000', '$2b$12$placeholder_hash_for_admin',  NULL, TRUE, TRUE),
    ('faria',  'Faria Islam',  'faria@example.com',  '01844444444', '$2b$12$placeholder_hash_for_faria',  NULL, TRUE, TRUE),
    ('mahmud', 'Mahmud Hasan', 'mahmud@example.com', '01766666666', '$2b$12$placeholder_hash_for_mahmud', NULL, TRUE, TRUE),
    ('nabila', 'Nabila Chowdhury', 'nabila@example.com', '01977777777', '$2b$12$placeholder_hash_for_nabila', NULL, TRUE, TRUE),
    ('arif',   'Arif Rahman',  'arif@example.com',  '01688888888', '$2b$12$placeholder_hash_for_arif',   NULL, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

INSERT INTO locations (location_name, campus_name, address, latitude, longitude)
VALUES
    ('TSC', 'University of Dhaka', 'TSC, Dhaka University', 23.7338, 90.3954),
    ('Central Library', 'University of Dhaka', 'Dhaka University', 23.7345, 90.3937),
    ('Shahbag', 'University of Dhaka', 'Shahbag, Dhaka', 23.7380, 90.3959),
    ('Dhanmondi', 'Campus A', 'Dhanmondi, Dhaka', 23.7465, 90.3760),
    ('Basundhara', 'Campus B', 'Basundhara, Dhaka', 23.8217, 90.4258),
    ('Science Lab', 'University of Dhaka', 'Science Lab, Dhaka', 23.7283, 90.3981)
ON CONFLICT DO NOTHING;

INSERT INTO items
    (seller_id, location_id, name, description, price, category,
     item_condition, available_from, status, video_url)
VALUES
    ((SELECT user_id FROM users WHERE username = 'rahim'),
     (SELECT location_id FROM locations WHERE location_name = 'TSC'),
     'HP Pavilion 15', 'Good-condition laptop for university work and coding assignments.', 55000,
     'Electronics', 'USED_GOOD', CURRENT_DATE, 'AVAILABLE',
     'https://www.youtube.com/watch?v=M7lc1UVf-VE'),
    ((SELECT user_id FROM users WHERE username = 'karim'),
     (SELECT location_id FROM locations WHERE location_name = 'Central Library'),
     'Scientific Calculator', 'Casio calculator suitable for engineering and business students.', 1200,
     'Study Material', 'USED_EXCELLENT', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'sakib'),
     (SELECT location_id FROM locations WHERE location_name = 'Shahbag'),
     'C++ Programming Book', 'A programming book in good condition with examples and exercises.', 800,
     'Books', 'USED_GOOD', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'nusrat'),
     (SELECT location_id FROM locations WHERE location_name = 'Dhanmondi'),
     'Office Chair', 'Comfortable study chair for room or hostel setup.', 3500,
     'Furniture', 'USED', CURRENT_DATE, 'SOLD', NULL),
    ((SELECT user_id FROM users WHERE username = 'tanvir'),
     (SELECT location_id FROM locations WHERE location_name = 'TSC'),
     'Mechanical USB Keyboard', 'New mechanical keyboard for long study sessions.', 2500,
     'Electronics', 'NEW', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'faria'),
     (SELECT location_id FROM locations WHERE location_name = 'Basundhara'),
     'Roadster Bike 2023', 'Single-owner bike, lightly used and maintained well.', 68000,
     'Bikes', 'USED_GOOD', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'mahmud'),
     (SELECT location_id FROM locations WHERE location_name = 'Science Lab'),
     'Lenovo ThinkPad X1', 'Thin and powerful laptop for software work and presentations.', 92000,
     'Electronics', 'USED_EXCELLENT', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'nabila'),
     (SELECT location_id FROM locations WHERE location_name = 'Dhanmondi'),
     'Study Desk with Shelf', 'Compact desk for a room, with extra shelf for books and accessories.', 6200,
     'Furniture', 'USED_GOOD', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'arif'),
     (SELECT location_id FROM locations WHERE location_name = 'Shahbag'),
     'Organic Chemistry Notes', 'Complete handwritten notes with summaries for exam preparation.', 1200,
     'Books', 'USED_EXCELLENT', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'rahim'),
     (SELECT location_id FROM locations WHERE location_name = 'TSC'),
     'Philips Bluetooth Speaker', 'Portable speaker with strong bass and deep connectivity.', 3600,
     'Electronics', 'NEW', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'karim'),
     (SELECT location_id FROM locations WHERE location_name = 'Central Library'),
     'Mini Fridge', 'Compact mini fridge for room utility and late-night snacks.', 14000,
     'Electronics', 'USED', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'sakib'),
     (SELECT location_id FROM locations WHERE location_name = 'Basundhara'),
     'Trek Mountain Bike', 'Good-condition mountain bike with new tires and front light.', 54000,
     'Bikes', 'USED_GOOD', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'nusrat'),
     (SELECT location_id FROM locations WHERE location_name = 'Science Lab'),
     'Cambridge IELTS Guide', 'Updated IELTS preparation guide with practice tests and answer keys.', 1500,
     'Books', 'USED_EXCELLENT', CURRENT_DATE, 'AVAILABLE', NULL),
    ((SELECT user_id FROM users WHERE username = 'tanvir'),
     (SELECT location_id FROM locations WHERE location_name = 'Dhanmondi'),
     'Standing Desk Converter', 'Adjustable desk converter for study-focused workspace setup.', 4800,
     'Furniture', 'NEW', CURRENT_DATE, 'AVAILABLE', NULL);

INSERT INTO item_media
    (item_id, media_type, storage_provider, media_url, public_id, original_filename, sort_order)
VALUES
    ((SELECT item_id FROM items WHERE name = 'HP Pavilion 15'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/hp-pavilion', 'hp-pavilion.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Scientific Calculator'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/calculator', 'calculator.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'C++ Programming Book'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/cpp-book', 'cpp-book.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Roadster Bike 2023'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/bike-1', 'roadster-bike.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Lenovo ThinkPad X1'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/thinkpad', 'thinkpad.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Study Desk with Shelf'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/desk', 'desk.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Organic Chemistry Notes'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/notes', 'notes.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Philips Bluetooth Speaker'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/speaker', 'speaker.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Mini Fridge'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/fridge', 'fridge.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Trek Mountain Bike'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/bike-2', 'trek-bike.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Cambridge IELTS Guide'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/ielts', 'ielts.jpg', 0),
    ((SELECT item_id FROM items WHERE name = 'Standing Desk Converter'), 'IMAGE', 'CLOUDINARY',
     'https://res.cloudinary.com/demo/image/upload/sample.jpg', 'demo/desk-converter', 'desk-converter.jpg', 0);

INSERT INTO posts (author_id, item_id, caption)
VALUES
    ((SELECT user_id FROM users WHERE username = 'rahim'),
     (SELECT item_id FROM items WHERE name = 'HP Pavilion 15'),
     'Selling my HP Pavilion laptop for a student who needs a reliable machine.'),
    ((SELECT user_id FROM users WHERE username = 'karim'),
     (SELECT item_id FROM items WHERE name = 'Scientific Calculator'),
     'Scientific calculator available for engineering students at a fair price.'),
    ((SELECT user_id FROM users WHERE username = 'sakib'),
     (SELECT item_id FROM items WHERE name = 'C++ Programming Book'),
     'My C++ programming book is ready to go to a new student owner.'),
    ((SELECT user_id FROM users WHERE username = 'nusrat'),
     (SELECT item_id FROM items WHERE name = 'Office Chair'),
     'Study chair available for an affordable price in good condition.'),
    ((SELECT user_id FROM users WHERE username = 'tanvir'),
     (SELECT item_id FROM items WHERE name = 'Mechanical USB Keyboard'),
     'Brand-new mechanical keyboard available for commuters and gamers.'),
    ((SELECT user_id FROM users WHERE username = 'faria'),
     (SELECT item_id FROM items WHERE name = 'Roadster Bike 2023'),
     'Low-mileage bike for campus commuting — clean and ready to ride.'),
    ((SELECT user_id FROM users WHERE username = 'nabila'),
     (SELECT item_id FROM items WHERE name = 'Study Desk with Shelf'),
     'Compact study desk with shelf for hostel rooms and small apartments.'),
    ((SELECT user_id FROM users WHERE username = 'arif'),
     (SELECT item_id FROM items WHERE name = 'Organic Chemistry Notes'),
     'Handwritten organic chemistry notes for exam prep and quick revision.'),
    ((SELECT user_id FROM users WHERE username = 'rahim'),
     (SELECT item_id FROM items WHERE name = 'Philips Bluetooth Speaker'),
     'Portable speaker with good sound quality and easy Bluetooth pairing.'),
    ((SELECT user_id FROM users WHERE username = 'sakib'),
     (SELECT item_id FROM items WHERE name = 'Trek Mountain Bike'),
     'Trek mountain bike available for a campus rider looking for a sturdy option.');

INSERT INTO post_reactions (post_id, user_id, reaction_type)
VALUES
    ((SELECT post_id FROM posts WHERE caption = 'Selling my HP Pavilion laptop for a student who needs a reliable machine.'), (SELECT user_id FROM users WHERE username = 'karim'), 'LIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'Selling my HP Pavilion laptop for a student who needs a reliable machine.'), (SELECT user_id FROM users WHERE username = 'sakib'), 'LIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'Scientific calculator available for engineering students at a fair price.'), (SELECT user_id FROM users WHERE username = 'rahim'), 'LIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'Scientific calculator available for engineering students at a fair price.'), (SELECT user_id FROM users WHERE username = 'faria'), 'DISLIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'My C++ programming book is ready to go to a new student owner.'), (SELECT user_id FROM users WHERE username = 'nusrat'), 'LIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'Study chair available for an affordable price in good condition.'), (SELECT user_id FROM users WHERE username = 'tanvir'), 'LIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'Low-mileage bike for campus commuting — clean and ready to ride.'), (SELECT user_id FROM users WHERE username = 'arif'), 'LIKE'),
    ((SELECT post_id FROM posts WHERE caption = 'Handwritten organic chemistry notes for exam prep and quick revision.'), (SELECT user_id FROM users WHERE username = 'mahmud'), 'LIKE');

INSERT INTO item_reactions (item_id, user_id, reaction_type)
VALUES
    ((SELECT item_id FROM items WHERE name = 'HP Pavilion 15'), (SELECT user_id FROM users WHERE username = 'karim'), 'LIKE'),
    ((SELECT item_id FROM items WHERE name = 'HP Pavilion 15'), (SELECT user_id FROM users WHERE username = 'sakib'), 'LIKE'),
    ((SELECT item_id FROM items WHERE name = 'Scientific Calculator'), (SELECT user_id FROM users WHERE username = 'rahim'), 'LIKE'),
    ((SELECT item_id FROM items WHERE name = 'Office Chair'), (SELECT user_id FROM users WHERE username = 'tanvir'), 'DISLIKE'),
    ((SELECT item_id FROM items WHERE name = 'Roadster Bike 2023'), (SELECT user_id FROM users WHERE username = 'arif'), 'LIKE'),
    ((SELECT item_id FROM items WHERE name = 'Lenovo ThinkPad X1'), (SELECT user_id FROM users WHERE username = 'faria'), 'LIKE'),
    ((SELECT item_id FROM items WHERE name = 'Philips Bluetooth Speaker'), (SELECT user_id FROM users WHERE username = 'mahmud'), 'LIKE'),
    ((SELECT item_id FROM items WHERE name = 'Cambridge IELTS Guide'), (SELECT user_id FROM users WHERE username = 'nabila'), 'LIKE');

INSERT INTO post_comments (post_id, author_id, comment_text)
VALUES
    ((SELECT post_id FROM posts WHERE caption = 'Selling my HP Pavilion laptop for a student who needs a reliable machine.'), (SELECT user_id FROM users WHERE username = 'karim'), 'Is the battery still in good condition?'),
    ((SELECT post_id FROM posts WHERE caption = 'Selling my HP Pavilion laptop for a student who needs a reliable machine.'), (SELECT user_id FROM users WHERE username = 'sakib'), 'Can we meet near TSC?'),
    ((SELECT post_id FROM posts WHERE caption = 'Scientific calculator available for engineering students at a fair price.'), (SELECT user_id FROM users WHERE username = 'rahim'), 'Is it still okay for engineering classes?'),
    ((SELECT post_id FROM posts WHERE caption = 'Low-mileage bike for campus commuting — clean and ready to ride.'), (SELECT user_id FROM users WHERE username = 'mahmud'), 'What is the exact mileage?'),
    ((SELECT post_id FROM posts WHERE caption = 'Handwritten organic chemistry notes for exam prep and quick revision.'), (SELECT user_id FROM users WHERE username = 'nabila'), 'Do you include previous year questions too?');

INSERT INTO item_comments (item_id, author_id, comment_text)
VALUES
    ((SELECT item_id FROM items WHERE name = 'HP Pavilion 15'), (SELECT user_id FROM users WHERE username = 'karim'), 'Is the battery condition good?'),
    ((SELECT item_id FROM items WHERE name = 'Scientific Calculator'), (SELECT user_id FROM users WHERE username = 'sakib'), 'Can I collect it from the library?'),
    ((SELECT item_id FROM items WHERE name = 'C++ Programming Book'), (SELECT user_id FROM users WHERE username = 'nusrat'), 'Which edition is this book?'),
    ((SELECT item_id FROM items WHERE name = 'Roadster Bike 2023'), (SELECT user_id FROM users WHERE username = 'tanvir'), 'Can I see the bike before buying?'),
    ((SELECT item_id FROM items WHERE name = 'Philips Bluetooth Speaker'), (SELECT user_id FROM users WHERE username = 'faria'), 'Does it support AUX too?');

INSERT INTO reviews (item_id, user_id, rating, review_text)
VALUES
    ((SELECT item_id FROM items WHERE name = 'HP Pavilion 15'), (SELECT user_id FROM users WHERE username = 'karim'), 5, 'The laptop was in very good condition and worked perfectly.'),
    ((SELECT item_id FROM items WHERE name = 'HP Pavilion 15'), (SELECT user_id FROM users WHERE username = 'sakib'), 4, 'Strong laptop, but the battery could be better.'),
    ((SELECT item_id FROM items WHERE name = 'Scientific Calculator'), (SELECT user_id FROM users WHERE username = 'rahim'), 5, 'Calculator works perfectly and is very useful for math classes.'),
    ((SELECT item_id FROM items WHERE name = 'C++ Programming Book'), (SELECT user_id FROM users WHERE username = 'nusrat'), 4, 'Book condition is good and easy to follow.'),
    ((SELECT item_id FROM items WHERE name = 'Roadster Bike 2023'), (SELECT user_id FROM users WHERE username = 'arif'), 5, 'Very smooth ride and well maintained.'),
    ((SELECT item_id FROM items WHERE name = 'Cambridge IELTS Guide'), (SELECT user_id FROM users WHERE username = 'nabila'), 5, 'Helpful for practice and speaking drills.');

INSERT INTO orders (item_id, buyer_id, seller_id, agreed_price, status)
VALUES
    ((SELECT item_id FROM items WHERE name = 'Office Chair'),
     (SELECT user_id FROM users WHERE username = 'rahim'),
     (SELECT user_id FROM users WHERE username = 'nusrat'), 3500, 'COMPLETED'),
    ((SELECT item_id FROM items WHERE name = 'Scientific Calculator'),
     (SELECT user_id FROM users WHERE username = 'sakib'),
     (SELECT user_id FROM users WHERE username = 'karim'), 1200, 'PENDING'),
    ((SELECT item_id FROM items WHERE name = 'Mechanical USB Keyboard'),
     (SELECT user_id FROM users WHERE username = 'faria'),
     (SELECT user_id FROM users WHERE username = 'tanvir'), 2500, 'CONFIRMED'),
    ((SELECT item_id FROM items WHERE name = 'Philips Bluetooth Speaker'),
     (SELECT user_id FROM users WHERE username = 'mahmud'),
     (SELECT user_id FROM users WHERE username = 'rahim'), 3600, 'PENDING');

INSERT INTO messages (sender_id, receiver_id, message_text, is_read)
VALUES
    ((SELECT user_id FROM users WHERE username = 'karim'), (SELECT user_id FROM users WHERE username = 'rahim'), 'Is the HP laptop still available?', TRUE),
    ((SELECT user_id FROM users WHERE username = 'rahim'), (SELECT user_id FROM users WHERE username = 'karim'), 'Yes, it is still available and the battery is fine.', TRUE),
    ((SELECT user_id FROM users WHERE username = 'sakib'), (SELECT user_id FROM users WHERE username = 'karim'), 'I want to buy the calculator. Is it still in stock?', FALSE),
    ((SELECT user_id FROM users WHERE username = 'faria'), (SELECT user_id FROM users WHERE username = 'arif'), 'Can I test ride the bike this weekend?', FALSE),
    ((SELECT user_id FROM users WHERE username = 'nabila'), (SELECT user_id FROM users WHERE username = 'nusrat'), 'Is the desk still available for pickup?', TRUE);

INSERT INTO notifications (user_id, notification_type, title, message, target_url, is_read)
VALUES
    ((SELECT user_id FROM users WHERE username = 'rahim'), 'REACTION', 'New Like', 'Karim liked your laptop listing.', '/items/1', FALSE),
    ((SELECT user_id FROM users WHERE username = 'rahim'), 'COMMENT', 'New Comment', 'Karim commented on your item.', '/items/1', FALSE),
    ((SELECT user_id FROM users WHERE username = 'karim'), 'ORDER', 'New Order', 'Someone placed an order for your calculator.', '/orders', FALSE),
    ((SELECT user_id FROM users WHERE username = 'faria'), 'MESSAGE', 'New Message', 'Arif replied about the bike test ride.', '/messages', FALSE),
    ((SELECT user_id FROM users WHERE username = 'nabila'), 'REACTION', 'Item Liked', 'Someone liked your study desk listing.', '/items/8', FALSE);

INSERT INTO item_predictions (item_id, model_name, predicted_category, confidence)
VALUES
    ((SELECT item_id FROM items WHERE name = 'Scientific Calculator'), 'campus-item-classifier-v1', 'Study Material', 0.9630),
    ((SELECT item_id FROM items WHERE name = 'Roadster Bike 2023'), 'campus-item-classifier-v1', 'Bikes', 0.9840),
    ((SELECT item_id FROM items WHERE name = 'Study Desk with Shelf'), 'campus-item-classifier-v1', 'Furniture', 0.9710),
    ((SELECT item_id FROM items WHERE name = 'Cambridge IELTS Guide'), 'campus-item-classifier-v1', 'Books', 0.9550);
