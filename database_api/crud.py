from database import get_connection
from models import EmailAnalysis


def save_email_analysis(data: EmailAnalysis):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO [dbo].[Emails] (
                [source_email_id],
                [thread_id],
                [sender],
                [subject],
                [received_at],
                [primary_category],
                [email_type],
                [summary],
                [schema_version],
                [processing_status]
            )
            OUTPUT INSERTED.email_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            data.source_email_id,
            data.thread_id,
            data.sender,
            data.subject,
            data.received_at.isoformat() if data.received_at else None,
            data.classification.primary_category,
            data.classification.email_type,
            data.summary,
            data.schema_version,
            data.processing_status
        )

        email_id = cursor.fetchone()[0]

        for tag_name in set(data.classification.tags):
            cursor.execute("""
                SELECT [tag_id]
                FROM [dbo].[Tags]
                WHERE [name] = ?
            """, tag_name)

            row = cursor.fetchone()

            if row:
                tag_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO [dbo].[Tags] ([name])
                    OUTPUT INSERTED.tag_id
                    VALUES (?)
                """, tag_name)

                tag_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO [dbo].[EmailTags] (
                    [email_id], [tag_id]
                )
                VALUES (?, ?)
            """, email_id, tag_id)

        for task in data.tasks:
            cursor.execute("""
                INSERT INTO [dbo].[Tasks] (
                    [email_id],
                    [title],
                    [description],
                    [deadline],
                    [priority],
                    [status]
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                email_id,
                task.title,
                task.description,
                task.deadline.isoformat() if task.deadline else None,
                task.priority,
                task.status
            )

        for event in data.events:
            cursor.execute("""
                INSERT INTO [dbo].[Events] (
                    [email_id],
                    [title],
                    [start_at],
                    [end_at],
                    [location]
                )
                VALUES (?, ?, ?, ?, ?)
            """,
                email_id,
                event.title,
                event.start_at.isoformat() if event.start_at else None,
                event.end_at.isoformat() if event.end_at else None,
                event.location
            )

        for evidence in data.evidence:
            cursor.execute("""
                INSERT INTO [dbo].[Evidence] (
                    [email_id],
                    [field_path],
                    [quote]
                )
                VALUES (?, ?, ?)
            """,
                email_id,
                evidence.field_path,
                evidence.quote
            )

        conn.commit()
        return email_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def get_all_emails():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                [email_id],
                [source_email_id],
                [sender],
                [subject],
                [summary],
                [primary_category],
                [email_type]
            FROM [dbo].[Emails]
            ORDER BY [email_id] DESC
        """)

        columns = [column[0] for column in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        conn.close()

def get_email_by_id(email_id: int):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                [email_id],
                [source_email_id],
                [thread_id],
                [sender],
                [subject],
                CONVERT(NVARCHAR(40), [received_at], 127) AS [received_at],
                [primary_category],
                [email_type],
                [summary],
                [schema_version],
                [processing_status],
                CONVERT(NVARCHAR(40), [created_at], 127) AS [created_at]
            FROM [dbo].[Emails]
            WHERE [email_id] = ?
        """, email_id)

        row = cursor.fetchone()

        if row is None:
            return None

        columns = [column[0] for column in cursor.description]
        email = dict(zip(columns, row))

        cursor.execute("""
            SELECT [tag_id], [name]
            FROM [dbo].[Tags]
            WHERE [tag_id] IN (
                SELECT [tag_id]
                FROM [dbo].[EmailTags]
                WHERE [email_id] = ?
            )
        """, email_id)

        email["tags"] = [
            {"tag_id": row[0], "name": row[1]}
            for row in cursor.fetchall()
        ]

        related_queries = {
            "tasks": """
                SELECT
                    [task_id],
                    [email_id],
                    [title],
                    [description],
                    CONVERT(NVARCHAR(40), [deadline], 127) AS [deadline],
                    [priority],
                    [status]
                FROM [dbo].[Tasks]
                WHERE [email_id] = ?
            """,
            "events": """
                SELECT
                    [event_id],
                    [email_id],
                    [title],
                    CONVERT(NVARCHAR(40), [start_at], 127) AS [start_at],
                    CONVERT(NVARCHAR(40), [end_at], 127) AS [end_at],
                    [location]
                FROM [dbo].[Events]
                WHERE [email_id] = ?
            """,
            "evidence": """
                SELECT *
                FROM [dbo].[Evidence]
                WHERE [email_id] = ?
            """
        }

        for key, query in related_queries.items():
            cursor.execute(query, email_id)

            columns = [column[0] for column in cursor.description]

            email[key] = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

        return email
    
    finally:
        conn.close()        
