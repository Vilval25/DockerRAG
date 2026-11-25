# Port publishing and mapping

Dominio: docker

Fuente: https://docs.docker.com/engine/network/port-publishing/

## Publishing ports

By default, Docker blocks access to container ports that have not been published. Use the `--publish` or `-p` flag with `docker run` or `docker create` to make a container port available through an address and port on the Docker host.

Publishing a port creates a host firewall rule that maps a container port to a port on the Docker host. This allows clients to reach the application through the host's network address.

## Port mapping syntax

The short syntax is:

```bash
docker run -p HOST_PORT:CONTAINER_PORT IMAGE
```

- `HOST_PORT` is the port on the Docker host that receives incoming traffic.
- `CONTAINER_PORT` is the port inside the container where the application is listening.

For example:

```bash
docker run -d -p 8080:80 nginx
```

This maps TCP port `8080` on the Docker host to port `80` inside the container. A request sent to port `8080` on the host is forwarded to port `80` in the container.

Other supported examples include:

```bash
docker run -p 192.168.1.100:8080:80 nginx
docker run -p 8080:80/udp nginx
docker run -p 8080:80/tcp -p 8080:80/udp nginx
```

The first example binds the published host port to the specified host IP address. The other examples specify the transport protocol for the published port.

## Binding a published port to a host address

The full syntax can include a host IP address:

```bash
docker run -p HOST_IP:HOST_PORT:CONTAINER_PORT IMAGE
```

If no host IP address is specified, Docker publishes the port on all host addresses by default (`0.0.0.0` and `[::]`). To make a published port accessible only from the Docker host, bind it to the loopback address:

```bash
docker run -p 127.0.0.1:8080:80 nginx
```

In this example, the published container port is reachable through `127.0.0.1:8080` from the Docker host.

## Security considerations

Publishing a container port makes it available not only to the Docker host but, by default, potentially to other systems that can reach the host. Do not publish sensitive services unintentionally.

Binding the published port to `127.0.0.1` limits access to the Docker host. The host IP, host port, container port, and optional protocol determine where the published service can be reached.

## Key points

- `-p` and `--publish` publish a container port through the Docker host.
- In `-p 8080:80`, `8080` is the host port and `80` is the container port.
- The host port is the entry point used by clients to reach the published service.
- Without an explicit host IP, Docker binds published ports to all host addresses by default.
- Publishing ports has security implications because the service may become reachable from outside the host.

