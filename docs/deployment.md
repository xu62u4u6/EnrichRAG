# Production Deployment

## Environment Variables

All configuration is via environment variables (or `.env` file). See `.env.example` for the full list.

### Security-critical settings

| Variable | Default | Production value | Notes |
|----------|---------|-----------------|-------|
| `AUTH_SECURE_COOKIES` | `false` | `true` | **Must** be `true` when serving over HTTPS, otherwise session cookies are sent in plaintext |
| `AUTH_INVITE_CODE` | `enrichrag-invite` | Change this | Required for user registration — treat as a shared secret |
| `LOG_LEVEL` | `INFO` | `WARNING` | Reduce log verbosity in production |

## Reverse Proxy (Nginx)

Set `URL_PREFIX` if EnrichRAG is served under a subpath:

```env
URL_PREFIX=/enrichrag
```

Example Nginx config:

```nginx
location /enrichrag/ {
    proxy_pass http://127.0.0.1:9001/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # SSE support
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
}
```

## SQLite File Permissions

The knowledge graph and auth databases are SQLite files stored at:

- KG: `~/.enrichrag/knowledge_graph/data/knowledge_graph.db`
- Auth/History: `~/.enrichrag/enrichrag.db` (or project-local)

For shared/lab environments:
- Ensure the process user has read/write access to both files and their parent directories
- SQLite uses WAL mode — the directory must also allow creating `-wal` and `-shm` files
- Do **not** place SQLite files on NFS or other network filesystems

## Security Checklist

- [ ] Set `AUTH_SECURE_COOKIES=true` (requires HTTPS)
- [ ] Change `AUTH_INVITE_CODE` from the default value
- [ ] Configure login rate limiting at the reverse proxy level
- [ ] Enable HTTPS with valid TLS certificate
- [ ] Restrict SQLite file permissions (`chmod 600`)
- [ ] Set `LOG_LEVEL=WARNING` to avoid leaking sensitive data in logs
