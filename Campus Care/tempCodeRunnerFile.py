def create_database(self) -> None:

        connection = None
        cursor = None

        try:
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )

            cursor = connection.cursor()

            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.database_name}`"
            )

            cursor.execute(
                f"USE `{self.database_name}`"
            )

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id VARCHAR(30) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    course VARCHAR(50) NOT NULL,
                    course_year INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    admin_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS complaints (
                    complaint_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(30) NOT NULL,
                    complaint_title VARCHAR(150) NOT NULL,
                    complaint_description TEXT NOT NULL,
                    status ENUM(
                        'Pending',
                        'In Progress',
                        'Solved'
                    ) NOT NULL DEFAULT 'Pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id)
                        REFERENCES students(student_id)
                )
            """)

            connection.commit()

            print("Database and tables are ready!")

        except Error as error:
            print("Database Setup Error:", error)

        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()

    # --------------------------------------------------
    # DATABASE CONNECTION
    # --------------------------------------------------

    def connect(self):

        try:
            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database_name
            )

        except Error as error:
            print("Database Connection Error:", error)
            return None

    # --------------------------------------------------
    # COMMON QUERY FUNCTION
    # --------------------------------------------------

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        fetch: Optional[str] = None
    ) -> Any:

        connection = self.connect()

        if connection is None:
            return None

        cursor = None

        try:
            cursor = connection.cursor(dictionary=True)

            cursor.execute(query, params)

            if fetch == "one":
                result = cursor.fetchone()

                if result is None:
                    return None

                return cast(QueryRow, result)

            if fetch == "all":
                result = cursor.fetchall()
                return cast(list[QueryRow], result)

            connection.commit()

            return cursor.rowcount

        except Error as error:
            connection.rollback()
            print("Database Error:", error)
            return None

        finally:
            if cursor is not None:
                cursor.close()

            if connection.is_connected():
                connection.close()

    # --------------------------------------------------
    # CHECK ADMIN
    # --------------------------------------------------

    def admin_exists(self) -> Optional[bool]:

        result = self.execute_query(
            "SELECT COUNT(*) AS total FROM admins",
            fetch="one"
        )

        if result is None:
            return None

        total = result["total"]

        if not isinstance(total, int):
            return None

        return total > 0

    # --------------------------------------------------
    # CREATE ADMIN
    # --------------------------------------------------

    def create_admin(
        self,
        username: str,
        password_hash: str
    ) -> Any:

        return self.execute_query(
            """
            INSERT INTO admins (username, password_hash)
            VALUES (%s, %s)
            """,
            (username, password_hash)
        )

    # --------------------------------------------------
    # GET ADMIN
    # --------------------------------------------------

    def get_admin(self, username: str) -> Optional[QueryRow]:

        return self.execute_query(
            "SELECT * FROM admins WHERE username = %s",
            (username,),
            fetch="one"
        )

    # --------------------------------------------------
    # REGISTER STUDENT
    # --------------------------------------------------

    def create_student(
        self,
        student_id: str,
        name: str,
        password_hash: str,
        course: str,
        course_year: int
    ) -> Any:

        return self.execute_query(
            """
            INSERT INTO students (
                student_id,
                name,
                password_hash,
                course,
                course_year
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                student_id,
                name,
                password_hash,
                course,
                course_year
            )
        )

    # --------------------------------------------------
    # GET STUDENT
    # --------------------------------------------------

    def get_student(
        self,
        student_id: str
    ) -> Optional[QueryRow]:

        return self.execute_query(
            "SELECT * FROM students WHERE student_id = %s",
            (student_id,),
            fetch="one"
        )

    # --------------------------------------------------
    # GET ALL STUDENTS
    # --------------------------------------------------

    def get_all_students(self) -> Optional[list[QueryRow]]:

        return self.execute_query(
            """
            SELECT
                student_id,
                name,
                course,
                course_year,
                created_at
            FROM students
            ORDER BY created_at DESC
            """,
            fetch="all"
        )

    # --------------------------------------------------
    # SUBMIT COMPLAINT
    # --------------------------------------------------

    def create_complaint(
        self,
        student_id: str,
        title: str,
        description: str
    ) -> Any:

        return self.execute_query(
            """
            INSERT INTO complaints (
                student_id,
                complaint_title,
                complaint_description
            )
            VALUES (%s, %s, %s)
            """,
            (student_id, title, description)
        )

    # --------------------------------------------------
    # GET COMPLAINTS
    # --------------------------------------------------

    def get_complaints(
        self,
        student_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[list[QueryRow]]:

        query = """
            SELECT
                c.complaint_id,
                c.student_id,
                s.name,
                c.complaint_title,
                c.complaint_description,
                c.status,
                c.created_at,
                c.updated_at
            FROM complaints c
            JOIN students s
                ON c.student_id = s.student_id
        """

        conditions: list[str] = []
        params: list[Any] = []

        if student_id is not None:
            conditions.append("c.student_id = %s")
            params.append(student_id)

        if status is not None:
            conditions.append("c.status = %s")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY c.created_at DESC"

        return self.execute_query(
            query,
            tuple(params),
            fetch="all"
        )

    # --------------------------------------------------
    # UPDATE COMPLAINT STATUS
    # --------------------------------------------------

    def update_complaint_status(
        self,
        complaint_id: int,
        status: str
    ) -> Any:

        return self.execute_query(
            """
            UPDATE complaints
            SET status = %s
            WHERE complaint_id = %s
            """,
            (status, complaint_id)
        )