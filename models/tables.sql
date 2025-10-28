-- user table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00
);
CREATE UNIQUE INDEX username ON users (username);

-- user's shares table
CREATE TABLE user_shares(
    id INTEGER PRIMARY kEY AUTOINCREMENT NOT NULL,
    user INTEGER NOT NULL, -- reference to user id and cascading
    symbol TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    sold_quantity INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- history table
CREATE TABLE user_histories(
    id INTEGER PRIMARY kEY AUTOINCREMENT NOT NULL,
    user INTEGER NOT NULL, -- reference to user id and cascading
    symbol TEXT NOT NULL,
    buying_price REAL NOT NULL,
    selling_price REAL,
    activity TEXT NOT NULL, -- buy or sell
    quantity INTEGER NOT NULL CHECK(quantity > 0),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
);