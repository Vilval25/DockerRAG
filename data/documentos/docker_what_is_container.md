# What is a container?

Dominio: docker

Fuente: https://docs.docker.com/learn/content/what-is-a-container/

Say you join a team that builds a to-do app. It has a Node.js backend, a React
frontend, and a database. Before you can work on it, you need the right version
of Node.js, the right database, and every library the app depends on.

Then the questions start. Is your Node.js the same version as your teammates’?
As the CI server’s? As production’s? What happens to the other project on your
laptop that needs an older Node.js? Each difference is a chance for the app to
work on one machine and fail on another.

Containers fix this by packaging an app together with everything it needs to
run, so it runs the same way on every machine that has Docker. This guide
explains what a container is, what an image is, and where images come from. It
doesn’t ask you to run anything; when you’re ready to, the
[next guide](#next) has you run the to-do app yourself.

## What a container is

A **container** is an ordinary process on your computer, such as a Node.js
server, that runs in isolation. It gets:

* **Its own filesystem.** The container sees only the files it was started
  with: its own operating system files, its own Node.js, its own libraries. It
  can’t see your files, and your other projects can’t see its files.
* **Its own view of the system.** It sees its own processes, its own network
  interfaces, and its own hostname, not the rest of your machine’s.
* **Limits you can set.** You can cap how much memory and CPU it uses.

Because everything the app needs is inside, a container doesn’t depend on what
is installed on your machine. Your to-do app’s backend can run on Node.js 22 in
one container while another project runs on an older Node.js in another, and
neither knows the other exists. Delete a container and nothing else on your
machine changes.

You’ll usually run one container for each part of an app: one for the backend,
one for the database. Each is started, stopped, and replaced on its own.

### Containers versus virtual machines

A **virtual machine** (VM) also isolates software, but it does so by pretending
to be a whole computer. Every VM boots its own complete operating system,
including its own kernel, the core of the operating system that talks to the
hardware.

A container doesn’t. It’s still a process, so every container on a machine
shares that machine’s kernel. There is no operating system to boot, which is why
a container starts in about a second and why one machine can run many of them.

The trade-off is that a VM’s isolation is stronger: containers that share a
kernel are separated by that kernel, while VMs are separated by the hardware
boundary the hypervisor creates.

In practice, you’ll often use both. Cloud servers are usually VMs that run many
containers each. And on macOS and Windows, Docker Desktop runs your Linux
containers inside a small Linux VM that it manages for you, because Linux
containers need a Linux kernel to share.

## What an image is

If a container is an isolated process with its own filesystem, where do those
files come from? From an **image**.

An image is a package of everything a container needs to start: the operating
system files, the language runtime, the app’s dependencies and code, and
settings such as which command to run. An image for the to-do app holds
Node.js, the app’s `node_modules`, and its source, and says “run
`node src/index.js`.”

Two properties make images useful:

* **Images are immutable.** Once built, an image never changes. Ten containers
  started from the same image start from exactly the same files, today or next
  month. To change an image, you build a new one.
* **Images are made of layers.** Each layer is a set of file changes: add these
  files, change those. A Node.js image is a Debian base layer plus a few layers
  that add Node.js. An image for your app starts from that and adds layers with
  your dependencies and code, so you never package Node.js yourself.

When a container starts, it uses the image’s layers as they are and adds one
thin **writable layer** of its own on top. Anything the running app writes,
such as a new to-do in its database, goes into that writable layer, never into
the image.

This explains two things you’ll run into early:

* **One image, many containers.** Containers don’t copy the image. They share
  its layers, so starting a second container from the same image is cheap.
* **Removing a container removes what it wrote.** The writable layer belongs to
  the container. Delete the container and the to-dos you added go with it. To
  keep data, you store it outside the container; see
  [Keep data with volumes and bind mounts](/learn/content/keep-data-with-volumes-and-bind-mounts/).

Layers are also shared *between* images. Every image built on the same Debian
base stores that base layer once, and downloads it once.

tip

**See an image’s layers in Docker Desktop.** Open the **Images** view and
select an image. Its detail page lists the layers that make it up, the base images it was built on, the
packages inside it, and any known vulnerabilities.

You build your own images from a recipe called a **Dockerfile**. The next path
starts there, in
[Write your first Dockerfile](/learn/content/write-your-first-dockerfile/), and
[How image layers and the build cache work](/learn/content/how-image-layers-and-the-build-cache-work/)
goes further into layers.

## Where images come from

Images are built once and then shared, so there has to be somewhere to share
them. That’s a **registry**: a service that stores images so anyone with access
can pull them. **Docker Hub** (`docker.io`) is Docker’s public registry and the
default one. If you don’t name a registry, Docker uses Docker Hub. Other
registries include GitHub Container Registry, Amazon ECR, Azure Container
Registry, and Google Artifact Registry, and companies often run their own.

Three words get mixed up here, so it’s worth pulling them apart:

* A **registry** is the service, such as Docker Hub.
* A **repository** is one named collection of images inside a registry, usually
  for one app. `library/node` holds Node.js images. A team’s
  `mobywhale/todo-app` would hold theirs.
* A **tag** names one image inside a repository, usually a version or variant:
  `22`, `22-slim`, `1.0`, `latest`. One image can carry several tags.

Put together, those parts make an image’s full name:

| Part | In `docker.io/library/node:22-slim` | If you leave it out |
| --- | --- | --- |
| Registry | `docker.io` | Docker uses Docker Hub |
| Repository | `library/node` | Required |
| Tag | `22-slim` | Docker uses `latest` |

The first part of a repository name is its **namespace**: a Docker Hub user or
organization, such as `mobywhale`. Docker Official Images live in the special
`library` namespace, which you can leave out too. That’s why `node:22-slim` and
`docker.io/library/node:22-slim` are the same image.

You can see all of this in one command. `docker pull` downloads an image from a
registry without running it. The terminal below is a simulation of a real run:
select the command to see what it prints. To try it on your own machine, you
need [Docker Desktop or Docker Engine](https://docs.docker.com/get-started/get-docker/).

Your machine

```
docker pull node:24-slim
```

```
24-slim: Pulling from library/node
9130dcb32e62: Pull complete
41b2195c3553: Already exists
80ce8e2829e2: Pull complete
98193c322145: Pull complete
f0255b2bdd97: Pull complete
Digest: sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205
Status: Downloaded newer image for node:24-slim
docker.io/library/node:24-slim
```

Read it from the top:

* **`Pulling from library/node`** is the repository. Docker filled in the
  `library` namespace for you.
* **Each line with an ID is a layer** being downloaded and unpacked.
* **`Already exists`** is layer sharing at work. This machine already had
  another image built on the same Debian base, so Docker skipped downloading
  that layer. On a fresh machine, you’d see `Pull complete` there instead.
* **`Digest`** is the image’s content fingerprint. A tag can be moved to a newer
  image later, but a digest always means exactly these bytes.
* **The last line** is the full name, with the registry and namespace filled in.

You don’t need to pull images by hand very often. `docker run` pulls the image
it needs if it isn’t on your machine yet.

note

The registry decides who can pull. A **public** repository can be pulled by
anyone; a **private** one only by accounts you grant access. Pushing an image to
a repository of your own is covered in
[Share your image on Docker Hub](/learn/content/share-your-image-on-docker-hub/).

## Images you can trust

Anyone can publish to Docker Hub, so an image’s name alone doesn’t tell you who
made it or whether it’s maintained. Docker Hub marks a few kinds of
**trusted content** with badges, and these are the images to start from:

* **Docker Official Images** are a curated set of images for operating systems,
  language runtimes, and common tools: `ubuntu`, `alpine`, `node`, `python`,
  `mysql`, and more. They’re documented, follow Dockerfile best practices, and
  are updated regularly. They’re the `library` namespace, so they have the
  shortest names. Most people start here.
* **Docker Hardened Images** are minimal, production-ready base images that
  Docker maintains with near-zero known vulnerabilities, and that come with
  signed security metadata such as a software bill of materials (SBOM) and
  provenance. They live in their own registry, so their names start with
  `dhi.io`, as in `dhi.io/node`, and pulling them requires signing in with a
  free Docker account. They’re free and open source under Apache 2.0.
* **Verified Publisher images** come from commercial software vendors whose
  identity Docker has verified.
* **Docker-Sponsored Open Source images** come from open source projects in
  Docker’s sponsorship program.

Everything else on Docker Hub is community content. Much of it is excellent,
but check who publishes it and how recently it was updated before you build on
it.

tip

For a comparison of Docker Official Images and Docker Hardened Images, and how to
choose one as the base for your own image, see
[Trusted content](https://docs.docker.com/docker-hub/image-library/trusted-content/)
and [Docker Hardened Images](https://docs.docker.com/dhi/) in the Docker Docs.
