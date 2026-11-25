# Keep data with volumes and bind mounts

Dominio: docker

Fuente: https://docs.docker.com/learn/content/keep-data-with-volumes-and-bind-mounts/

You start a to-do app in a container, add a few items, and later replace the
container with a fresh one, perhaps to pick up a new image. Your to-dos are
gone. Nothing crashed. A container keeps the files it writes inside itself,
and removing the container removes them too.

That’s the right default for most files, but not for the data you care about.
In this guide, you’ll watch the to-dos disappear, then keep them two ways: in a
**named volume** that Docker manages, and in a **bind mount** of a directory on
your own disk. You’ll make a mount read-only, see what happens when the app
tries to write to it anyway, and finish with a rule of thumb for choosing
between the two.

## Before you start

You can follow this whole guide in your browser. The terminals on this page
are simulations: click through them to see what each command does and what it
prints.

To run it for real on your own machine, you need:

* **Docker Desktop or Docker Engine.** See
  [Get Docker](https://docs.docker.com/get-started/get-docker/).
* **The sample app’s image.** The guide uses the
  [getting-started to-do app](https://github.com/docker/getting-started-todo-app),
  which has no published image, so build it straight from its Git repository.
  This takes about a minute:

  ```
  $ docker build -t todo-app https://github.com/docker/getting-started-todo-app.git
  ```

  How that build works is the subject of
  [Write your first Dockerfile](/learn/content/write-your-first-dockerfile/).
  For this guide, you only need the image.
* **`curl`**, to talk to the app’s API. You can also open
  <http://localhost:3000> and add to-dos in your browser instead.

The app stores its to-dos in a SQLite database file at `/etc/todos/todo.db`
inside the container. That one directory, `/etc/todos`, is what this guide
keeps.

Your output will differ from the simulations in the details: container IDs,
to-do IDs, and timestamps.

## Step 1: Watch the data disappear

Start the app, add a to-do, and list what’s stored:

Host machine

```
docker run -d -p 3000:3000 --name todo todo-app
```

```
cec84effe9586833d7352ad483ffa7b86af5108bbef3e3bf5591b239cb6adbae
```

```
curl -s -X POST localhost:3000/api/items -H "Content-Type: application/json" -d '{"name": "Buy milk"}'
```

```
{"id":"c0d14300-3d0b-4d12-ba47-dbb2e1913fa5","name":"Buy milk","completed":false}
```

```
curl -s localhost:3000/api/items
```

```
[{"id":"c0d14300-3d0b-4d12-ba47-dbb2e1913fa5","name":"Buy milk","completed":false}]
```

Now do what you’d do to upgrade the app: remove the container and start a new
one from the same image. `docker rm -f` stops and removes it in one go.

Host machine

```
docker rm -f todo
```

```
todo
```

```
docker run -d -p 3000:3000 --name todo todo-app
```

```
8e82f3b847930a4fce1e3b3b019f1d8f038406c9048fd6bb82084b1946e3acd2
```

```
curl -s localhost:3000/api/items
```

```
[]
```

An empty list. The new container started from the image, and the image has
never contained your to-dos.

Here’s why. An image is read-only. When a container starts, Docker gives it a
thin **writable layer** on top of the image, and every file the container
creates or changes lands there, including `todo.db`. The writable layer
belongs to that one container, and `docker rm` deletes it.

To keep a file, it has to live somewhere outside the writable layer. Docker
does that with a **mount**: you attach storage from outside the container at a
path inside it, and reads and writes to that path go to the storage instead.

Docker has two kinds of mount for this: a volume and a bind mount. You’ll use
one at a time, at the same path.

## Step 2: Keep the data in a named volume

A **named volume** is storage that Docker creates and manages for you. You
refer to it by name, and it exists independently of any container.

Remove the container from Step 1, then start a new one with `-v todo-data:/etc/todos`. The part before the colon is the volume’s name; the
part after is where it appears inside the container. If no volume called
`todo-data` exists yet, Docker creates it.

Host machine

```
docker rm -f todo
```

```
todo
```

```
docker run -d -p 3000:3000 --name todo -v todo-data:/etc/todos todo-app
```

```
41c538ab12c2f72d1a0da53ea336d4cb54e498c48fcf52f81bac9df3bf4e106c
```

```
curl -s -X POST localhost:3000/api/items -H "Content-Type: application/json" -d '{"name": "Buy milk"}'
```

```
{"id":"a42b08f7-1ead-4961-94f6-f97d9e4dfa17","name":"Buy milk","completed":false}
```

```
curl -s -X POST localhost:3000/api/items -H "Content-Type: application/json" -d '{"name": "Walk the dog"}'
```

```
{"id":"20d2f4be-4a78-468d-bb01-c61870835854","name":"Walk the dog","completed":false}
```

Now the same test that lost your data in Step 1: remove the container and
start a brand-new one, attaching the same volume.

Host machine

```
docker rm -f todo
```

```
todo
```

```
docker run -d -p 3000:3000 --name todo -v todo-data:/etc/todos todo-app
```

```
43e225e9a3280319e8f7293f5aca0bfe14f39363e0811a18e30ce323c7f378d3
```

```
curl -s localhost:3000/api/items
```

```
[{"id":"a42b08f7-1ead-4961-94f6-f97d9e4dfa17","name":"Buy milk","completed":false},{"id":"20d2f4be-4a78-468d-bb01-c61870835854","name":"Walk the dog","completed":false}]
```

Both to-dos survived, with the same IDs. The old container is gone, but
`todo.db` was never in it: it was in the volume.

### Look at the volume

A volume is a Docker object, like a container or an image, with its own
commands. List your volumes and inspect this one:

Host machine

```
docker volume ls
```

```
DRIVER    VOLUME NAME
local     todo-data
```

```
docker volume inspect todo-data
```

```
[
    {
        "CreatedAt": "2026-10-21T20:18:19Z",
        "Driver": "local",
        "Labels": null,
        "Mountpoint": "/var/lib/docker/volumes/todo-data/_data",
        "Name": "todo-data",
        "Options": null,
        "Scope": "local"
    }
]
```

```
docker volume rm todo-data
```

```
Error response from daemon: remove todo-data: volume is in use - [43e225e9a3280319e8f7293f5aca0bfe14f39363e0811a18e30ce323c7f378d3]
```

`Mountpoint` is where the volume’s files live, inside Docker’s own storage
area. With Docker Desktop, that path is inside Docker’s Linux VM, not on your
Mac or Windows file system. Either way, it’s Docker’s to manage: you work with
the data through containers, not by editing that directory.

The failed `docker volume rm` is deliberate. Docker won’t remove a volume that
a container is using, and it names the container that holds it. A volume also
outlives every container that used it, so it stays on disk until you remove
it. You’ll clean it up at the end of this guide.

tip

**Browse a volume’s files in Docker Desktop.** The **Volumes** view lists your volumes. Select one to see
which container is using it on the **Container in-use** tab and browse its
files on the **Stored data** tab. See
[Explore the Volumes view](https://docs.docker.com/desktop/use-desktop/volumes/).

### The same mount, written with `--mount`

`-v` is short. Docker also accepts a longer form, `--mount`, which spells each
part out as a key-value pair. These two flags do the same thing:

```
-v todo-data:/etc/todos
--mount type=volume,src=todo-data,dst=/etc/todos
```

Replace the container once more, this time with `--mount`:

Host machine

```
docker rm -f todo
```

```
todo
```

```
docker run -d -p 3000:3000 --name todo --mount type=volume,src=todo-data,dst=/etc/todos todo-app
```

```
cbd2d2c95686fb9f50d37fc8c789bb17299469a0373341aff7412dd54cb138fe
```

```
curl -s localhost:3000/api/items
```

```
[{"id":"a42b08f7-1ead-4961-94f6-f97d9e4dfa17","name":"Buy milk","completed":false},{"id":"20d2f4be-4a78-468d-bb01-c61870835854","name":"Walk the dog","completed":false}]
```

Same volume, same data. The rest of this guide uses `-v` because it’s shorter
to read. The Docker documentation generally prefers `--mount`, because it’s
more explicit and supports every option, some of which `-v` can’t express. See
[Volumes](https://docs.docker.com/engine/storage/volumes/#syntax) for the
differences.

## Step 3: Share a directory with a bind mount

A volume keeps your data safe, but you can’t easily see it: it lives in
Docker’s storage area. Sometimes you want the opposite. You want the file on
your own disk, where your editor, your backup tool, or a database browser can
reach it.

A **bind mount** attaches a directory from your machine at a path inside the
container. It’s the same directory, seen from two places: whatever the
container writes there appears on your disk, and whatever you put there
appears inside the container.

Replace the container, create a `data` directory in your current directory,
and bind-mount it at `/etc/todos`. With `-v`, a source that starts with `/`
is a path on your machine; a plain name, like `todo-data`, is a volume.
`$(pwd)` expands to the full path of your current directory.

Host machine

```
docker rm -f todo
```

```
todo
```

```
mkdir data
```

```
docker run -d -p 3000:3000 --name todo -v "$(pwd)/data:/etc/todos" todo-app
```

```
aab20c5678ad412a20ae1517f3de257e484cdcb2b971381e572f08996b27ccbd
```

```
ls data
```

```
todo.db
```

```
curl -s -X POST localhost:3000/api/items -H "Content-Type: application/json" -d '{"name": "Buy milk"}'
```

```
{"id":"690b8825-5e5a-4334-978c-e3bf2fa10f7d","name":"Buy milk","completed":false}
```

`todo.db` is now an ordinary file in `data` on your machine. The app created
it at startup, and every to-do you add is written to it. This is a fresh,
empty database: the to-dos in the `todo-data` volume are still there, but this
container isn’t using the volume.

note

Create the directory before you mount it. If it doesn’t exist, `-v` creates it
for you, but on Linux with Docker Engine that directory is owned by `root`,
which makes it awkward to edit or delete. (`--mount` refuses to start the
container instead.)

The mount works in the other direction too. Write a file into `data` on your
machine, and look for it from inside the running container:

Host machine

```
echo 'Back up todo.db before upgrading' > data/notes.txt
```

```
docker exec todo ls /etc/todos
```

```
notes.txt
todo.db
```

```
docker exec todo cat /etc/todos/notes.txt
```

```
Back up todo.db before upgrading
```

There’s no copying involved. The container sees the change the moment you
make it, because it’s looking at the same directory. That’s what makes bind
mounts the tool for source code and configuration you’re editing.

Remove the container, and the files stay where they are, on your disk:

Host machine

```
docker rm -f todo
```

```
todo
```

```
ls data
```

```
notes.txt
todo.db
```

## Step 4: Make a mount read-only

The container can change or delete anything in a bind-mounted directory,
because it’s your directory. When a container only needs to read files, such
as configuration, add `:ro` to the end of the mount to make it read-only.

To see what read-only means, mount `data` read-only and try to use the app as
usual. Reading works. Adding a to-do does not:

Host machine

```
docker run -d -p 3000:3000 --name todo -v "$(pwd)/data:/etc/todos:ro" todo-app
```

```
c179c7e0580a0071f95933c5137f57077bb33b05c601da86d213e30c18039226
```

```
curl -s localhost:3000/api/items
```

```
[{"id":"690b8825-5e5a-4334-978c-e3bf2fa10f7d","name":"Buy milk","completed":false}]
```

```
curl -s -X POST localhost:3000/api/items -H "Content-Type: application/json" -d '{"name": "Call the vet"}'
```

```
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Error</title>
</head>
<body>
<pre>Internal Server Error</pre>
</body>
</html>
```

```
docker logs todo
```

```
Using sqlite database at /etc/todos/todo.db
Listening on port 3000
Error: SQLITE_READONLY: attempt to write a readonly database
```

```
docker exec todo touch /etc/todos/test.txt
```

```
touch: cannot touch '/etc/todos/test.txt': Read-only file system
```

That error is the point. The app read `todo.db` and served the existing
to-do, but SQLite couldn’t write to it, and even `touch` running as `root`
inside the container can’t create a file. The container can’t change what you
mounted read-only, whatever it runs as.

A database is the wrong thing to mount read-only, which is why the app broke.
Use `:ro` for files the container should consume but never change: a config
file, certificates, or source code that a container only serves. `:ro` works
the same way on a volume.

## Step 5: Choose between a volume and a bind mount

Both mounts keep data outside the container. What differs is who owns the
data.

|  | Named volume | Bind mount |
| --- | --- | --- |
| Where the data lives | Docker’s storage area, by name | A directory you choose on your machine |
| Who manages it | Docker: `docker volume ls`, `inspect`, `rm` | You: your file manager, editor, and backups |
| Starts out | Empty, or seeded from the image’s files at that path | With whatever is already in your directory |
| Depends on your machine | No: same name, same behavior anywhere Docker runs | Yes: the path has to exist on that machine |
| Reach for it for | Data the app owns: databases, uploads, caches you want to keep | Files you edit on the host: source code, config |

The rule of thumb: **if the application owns the data, use a volume. If you
own the files and want to edit them on your machine, use a bind mount.** Add
`:ro` to either when the container should only read.

For the to-do app, the database belongs in a volume. The bind mount in Step 3
was useful for seeing `todo.db`, but in practice you’d keep the database in a
volume and bind-mount your source code instead, so the container picks up
your edits.

note

With Docker Desktop, the Docker daemon runs in a Linux VM, and Docker Desktop
shares your bind-mounted directories into it for you. Volumes live inside the
VM. The Docker documentation also points to volumes for data that needs
high-performance I/O, such as a database. See
[Volumes](https://docs.docker.com/engine/storage/volumes/#when-to-use-volumes).

Try the rule on some cases:

## Clean up

Remove the container, the volume, and the `data` directory. A volume is never
removed with its container, so it needs its own `docker volume rm`, which
works now that nothing is using it:

Host machine

```
docker rm -f todo
```

```
todo
```

```
docker volume rm todo-data
```

```
todo-data
```

```
rm -rf data
```

```
docker volume ls
```

```
DRIVER    VOLUME NAME
```

If you have other volumes, `docker volume ls` lists them too. Don’t reach for
`docker volume prune` to tidy up unless you mean it: it removes every volume
that no container is using, including ones you meant to keep.

## What you learned

* A container writes to its own **writable layer**, and `docker rm` deletes
  it, along with anything the app stored there.
* A **mount** attaches storage from outside the container at a path inside
  it, so the data outlives the container.
* A **named volume** (`-v todo-data:/etc/todos`) is storage Docker manages.
  You list, inspect, and remove it with `docker volume`, and Docker won’t
  remove one that’s in use.
* A **bind mount** (`-v "$(pwd)/data:/etc/todos"`) shares a directory on
  your machine. Changes on either side are visible on the other immediately.
* **`:ro`** makes a mount read-only. A write fails with a read-only file
  system error, even for `root` in the container.
* Use a volume for data the application owns, and a bind mount for files you
  edit on your machine.
