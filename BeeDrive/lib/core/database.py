from ..encrypt import sha256_encode, CHARS, create_salt


class UserDatabase:

    "New Feature for Version 4.1."
    
    def __init__(self, root):
        os.makedirs(os.path.split(root)[0], exist_ok=True)
        self.root = root
        self.maxtry = 3
        self.conn = None
        self.curs = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.root)
        self.curs = self._conn.cursor()
        self.curs.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ("users",))
        if self.curs.fetchone() is None:
            self.curs.execute("CREATE TABLE users(name, passwd, salt, admin, retry)")

    def __exist__(self, exc_type, exc_val, exc_tb):
        self.curs.close()
        self.conn.close()
        self.curs, self.conn = None, None

    def _encode(self, passwd, salt):
        passwd = passwd + "$" + salt
        return sha256_encode(passwd)

    def list_users(self):
        with self:
            rslt = self.curs.execute("SELECT name FROM users")
            return rslt.fetchall()

    def clear(self):
        with self:
            self.curs.execute("DROP TABLE IF EXISTS users")
            self.conn.commit()

    def verify_login(self, name, passwd):
        assert isinstance(name, str) and isinstance(passwd, str)
        with self:
            rslt = self.curs.execute("SELECT passwd, salt, retry FROM users WHERE name=?", (name,)).fetchone()
            if rslt is None:
                return False
            if int(rslt[2]) == self.maxtry:
                return "This account has been locked."
            passwd = self._encode(passwd, rslt[1])
            success = passwd == rslt[0]
            if success:
                self.curs.execute("UPDATE users SET retry=0 WHERE name=?", (name,))
            else:
                self.curs.execute("UPDATE users SET retry=retry+1 WHERE name=?", (name,))
            self.conn.commit()
            return success
            

    def create_user(self, name, passwd, admin):
        assert isinstance(name, str) and isinstance(passwd, str)
        assert isinstance(admin, bool) and admin in (1, 0)
        if len(name) < 4:
            return "User name needs at least 4 chars."
        if len(set(passwd)) < 4:
            return "Password needs at least 4 unique chars."
        with self:
            rslt = self.curs.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
            if rslt is not None:
                return "User name has been taken."
            salt = create_salt(8)
            passwd = self._encode(passwd, salt)
            self.curs.execute("INSERT INTO users VALUES(?, ?, ?, ?, ?)", [name, passwd, salt, admin, 0])
            self.conn.commit()
            return "Successs"

    def reset_passwd(self, name, passwd):
        assert isinstance(passwd, str)
        if len(set(passwd)) < 4:
            return "Password needs at least 4 unique chars."
        with self:
            rslt = self.curs.execute("SELECT salt FROM users WHERE name=?", (name,)).fetchone()
            if rslt is None:
                return "User name doesn exist."
            passwd = self._encode(passwd, rslt[0])
            self.curs.execute("UPDATE users SET passwd=? WHERE name=?", (passwd, name))
            self.conn.commit()
