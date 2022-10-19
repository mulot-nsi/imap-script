import argparse
import csv
import email.header
import email.utils
import imaplib
import json
import os


class Students:
    db = []

    def add_from_csv(self, path):
        with open(path) as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.add(row["nom"], row["prenom"], row["classe"])

    def add(self, nom, prenom, classe):
        self.db.append({"nom": nom, "prenom": prenom, "classe": classe})

    def search(self, query):
        found1 = []
        found2 = []

        for student in self.db:
            if student["nom"].find(" ") == -1:  # Nom simple (ne contient pas d'espace)
                if student["nom"] in query.split():
                    found1.append(student)
            else:  # Nom composé
                if student["nom"] in query:
                    found1.append(student)

        if len(found1) > 1:
            for student in found1:
                # Prénom simple (ne contient pas d'espace)
                if student["prenom"].find(" ") == -1:
                    if student["prenom"] in query.split():
                        found2.append(student)
                else:  # Prénom composé
                    if student["prenom"] in query:
                        found2.append(student)
        else:
            found2 = found1

        return found2[0] if len(found2) == 1 else None


def get_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    return parser


def load_config(path):
    with open(path) as f:
        return json.load(f)


def load_csv_files(directory_path):
    students = Students()

    for file in os.listdir(directory_path):
        if file.endswith(".csv"):
            students.add_from_csv(os.path.join(directory_path, file))
    return students


def decode_real_name(realname):
    decoded_parts = []

    for part in email.header.decode_header(realname):
        if part[1] is not None:
            decoded = part[0].decode(part[1])
        elif isinstance(part[0], bytes):
            decoded = part[0].decode("ascii").strip()
        else:
            decoded = part[0]
        decoded_parts.append(decoded)

    return ' '.join(decoded_parts)


def sort_students(config, students):
    imap_config = config["imap"]
    server = imaplib.IMAP4_SSL(imap_config["host"], imap_config["port"])
    server.login(imap_config["user"], imap_config["password"])

    server.select("INBOX")
    _, msgnums = server.search(None, 'ALL')

    for num in msgnums[0].split():
        _, data = server.fetch(num, 'BODY.PEEK[HEADER.FIELDS (FROM)]')
        real_name, email_address = email.utils.parseaddr(str(data[0][1]))
        real_name = decode_real_name(real_name)
        student = students.search(real_name)

        output_message = real_name

        if student:
            output_message += f" - \033[35m{student['prenom']} {student['nom']}\033[0m"

            status, _ = server.copy(num, "INBOX/ELEVES/" + student["classe"])
            if status == 'OK':
                server.store(num, '+FLAGS', '\\Deleted')
                output_message += f" - \033[32mMoved to {student['classe']}\033[0m"
            else:
                output_message += f" - \033[31mIssue during copy to {student['classe']}\033[0m"

        else:
            output_message += " - \033[36mNot student\033[0m"
        print(output_message)

    server.expunge()


def run():
    args = get_argparse().parse_args()
    config = load_config(args.config)
    students = load_csv_files(config["student_csv_directory"])
    sort_students(config, students)


if __name__ == '__main__':
    run()
