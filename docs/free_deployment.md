# Free public demo deployment

The repository is prepared for a free Render Web Service deployment through
[`render.yaml`](../render.yaml) and the included `Dockerfile`.

## What is free and what is not

Render's free web service is suitable for a hackathon demo. Current free-plan
limitations include approximately 0.1 CPU, 512 MB RAM, automatic sleep after
15 minutes without traffic, approximately one minute cold starts, ephemeral
local storage, and a monthly included instance-hour allowance.

The web host can be free, but Nebius Token Factory and Tavily API requests may
still consume account credits or incur usage charges. Monitor both accounts
and use the smallest demo workload.

## Deployment steps

1. Push this repository to a public GitHub, GitLab, or Bitbucket repository.
2. Create a Render account.
3. Choose **New → Blueprint** and connect the public repository.
4. Render detects `render.yaml` and creates the `centri-demo` free web service.
5. Enter these secret environment values in Render:

   ```text
   NEBIUS_API_KEY=<your Nebius Token Factory key>
   TAVILY_API_KEY=<your Tavily key>
   ```

6. Deploy and wait for the Docker build and first-time index compilation.
7. Open the generated URL:

   ```text
   https://centri-demo.onrender.com/health
   ```

8. Confirm that the response reports a loaded HNSW index.
9. Use the public `/docs` page as the working demo URL:

   ```text
   https://centri-demo.onrender.com/docs
   ```

## Hackathon demo calls

Routing:

```bash
curl --location "https://centri-demo.onrender.com/route" \
  --header "Content-Type: application/json" \
  --data '{"query":"My VPN stopped after a password change."}'
```

Runtime Tavily qualification:

```bash
curl --location "https://centri-demo.onrender.com/chat" \
  --header "Content-Type: application/json" \
  --data '{"prompt":"What are the latest enterprise security updates relevant to our IT policy?","use_web_search":true}'
```

The `/chat` response includes a `web_research` object showing whether Tavily
was called and the returned source summaries. This is the call to record in
the hackathon demo video.

## Demo caveats

- Free Render services sleep when idle, so the first request may be slow.
- The compiled index is generated during startup and local files are
  ephemeral; this is acceptable for a demo but not a production deployment.
- The sample agents use `CENTRI_MOCK_EXECUTION=true` unless real HTTP runtime
  endpoints are configured.
- Do not expose API keys in the repository, screenshots, video, or public
  logs.
- Set `CENTRI_AUTH_REQUIRED=true` and configure a strong JWT secret before
  exposing any real enterprise data or agent runtime.

Official hosting references:

- [Render free services](https://render.com/docs/free)
- [Render web services](https://render.com/docs/web-services)
- [Render compute plans](https://render.com/docs/compute-plans)

