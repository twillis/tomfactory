## Deleting a file

You have no tool that deletes a file, and you need none: to delete one, list it under `delete` in your reply's JSON
object, each as its path relative to the current directory (`"delete": ["path/to/old.py"]`). The factory deletes
each after your step, and judges the deletion as it judges any other change: only a file this step may change, and
only inside the current directory. A file deleted that way is committed with the rest of your work. Leave `delete`
out if you delete nothing.
