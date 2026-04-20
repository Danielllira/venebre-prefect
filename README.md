# Overview

I wanted to build a real data platform foundation, something that could actually make sense for a small startup starting from zero, but still be simple enough to run, understand, and improve over time

A big reason why I started this project is because, as a data engineer, I got very used to building ETL and ELT pipelines in day to day work, and after some time some of the more basic infra concepts start getting a bit blurred You keep using the tools, but sometimes you are not really thinking that much about what is happening underneath

So this project became a way to go back to that a little bit and understand things better under the hood Not only from the data side, but also from the platform side too, orchestration, execution, auth, reverse proxy, HTTPS, containers, deploy flow, all of that

The idea was basically to create a real and functional data platform, like something a startup could actually use in the beginning, not something huge, not something overengineered, but also not just a toy project
<img width="1487" height="855" alt="image" src="https://github.com/user-attachments/assets/c3bd5804-5f11-4d64-8ed7-57a21b800b33" />


---

## What this project is trying to do

At a high level, the idea is pretty simple

- keep a self hosted orchestration layer
- run the actual flow executions in Cloud Run Jobs
- separate dev and prod from the start
- automate image build and deployment
- keep the whole thing small, understandable, and cheap enough to maintain

So yeah, this is meant to be a real platform for real pipelines, just with startup constraints in mind

---

## Architecture in a nutshell

The platform is basically split into two big parts

### 1 Control plane

The control plane runs on a single VM and contains

- Nginx
- Prefect Server
- Prefect Services
- PostgreSQL
- Redis
- Prefect Workers

This VM is kind of the brain of the platform

It hosts the Prefect UI and API, keeps the state, schedules runs, and has the workers that submit jobs to the execution layer

Nginx sits in front of everything and exposes the Prefect UI through [pipelines.venebre.com](https://pipelines.venebre.com), with HTTPS and Basic Auth

PostgreSQL stores Prefect state, Redis supports the messaging/cache side, and then there are two separate workers

- one for dev
- one for prod

Each one listens to its own work pool, which made things way easier to reason about later

### 2 Execution plane

The actual flow runs do not happen inside the VM

When a deployment is triggered, the worker submits a Cloud Run Job That job spins up with the correct runtime image, the correct service account, runs the flow, reports the result back to Prefect, and then gets cleaned up

This separation was one of the most important choices in the whole project

I really did not want the VM doing the heavy work itself I wanted it to coordinate, not become the place where all the actual execution happens

That keeps the architecture cleaner and also makes the whole thing feel a lot more real

---

## Main stack

The main tools used here are

- Prefect 3 for orchestration
- Google Cloud Run Jobs for execution
- Google Compute Engine for the self hosted control plane
- PostgreSQL for Prefect state
- Redis for messaging/cache support
- Nginx as reverse proxy
- Docker Compose for the self hosted stack
- Artifact Registry for runtime images
- GitHub Actions for build and deploy automation
- Workload Identity Federation for secure GitHub ↔ GCP auth
- Secret Manager for runtime secrets
- Let’s Encrypt / Certbot for HTTPS

Nothing too crazy tbh, but together it gives a very solid base

---

## Environments

The platform currently works with two logical environments

- dev
- prod

Even though the control plane lives in a single VM, dev and prod are separated in the parts that actually matter

- different work pools
- different workers
- different runtime images
- different service accounts
- different GCP projects
- different deployment names and settings

This was intentional from the beginning because I did not want the usual situation where everything is mixed at first and then later it becomes annoying to untangle

---

## How deploys work

The deploy flow is split into two main parts

First, GitHub Actions builds and pushes the runtime image to Artifact Registry based on the branch

- dev branch → dev image
- main branch → prod image

After that, the workflow publishes the changed flows to Prefect using `flow.deploy(...)`

The naming is simple

- in dev, deployments get ` - Dev`
- in prod, deployments keep the original flow name

So if the flow is called

- `Extract - API Weather Data`

the deployments become

- `Extract - API Weather Data - Dev`
- `Extract - API Weather Data`

Small detail, but it makes the UI much easier to read

---

## Security and auth

Security here was done in layers

The Prefect UI is behind HTTPS + Basic Auth through Nginx That was the simplest setup that still felt serious enough for this kind of project

For GitHub Actions, auth to GCP is done with Workload Identity Federation, so there is no long lived JSON key hanging around

For flow execution, Cloud Run Jobs use environment specific service accounts with the minimum roles they need The runtime also gets the Prefect API URL and auth string so it can talk back to the self hosted Prefect API through the public HTTPS endpoint

This part took some time to get right tbh, but once it clicked the whole setup started making a lot more sense

---

## Why this architecture

A few decisions shaped the project a lot

### Self hosted Prefect instead of Prefect Cloud

This was partly about cost and control, but honestly also about learning

I wanted to understand what the control plane actually looks like when you host it yourself How the UI is exposed, how workers connect, how runtime jobs authenticate back to the API, how state is stored, and what details start to matter once things become a little more real

### One VM for the control plane

I did not want to start with multiple VMs, HA, load balancers, or anything too big too early

A single VM is enough for this stage, specially because the heavy execution is offloaded to Cloud Run It keeps the setup much more understandable and cheaper to run, which matters a lot for a project like this

### Cloud Run Jobs for execution

This was probably the biggest architectural choice

Instead of executing flows directly on the VM, the VM only orchestrates and submits jobs The flow code itself runs in Cloud Run, which gives much better isolation and makes the platform cleaner overall

It also forced me to understand better where config actually belongs

- what stays in the worker
- what stays in the work pool
- what goes into the runtime image
- what has to be passed into the job execution itself

That alone already made the whole project worth it

---

## Challenges along the way

A few things were a bit more annoying than I expected, but in a good way

One of the biggest ones was understanding the difference between what works inside the VM and what works inside the Cloud Run Job

That sounds obvious when written like this, but in practice it caused some of the most useful debugging moments in the project A worker talking to `prefect-server` internally is one thing A job running in Cloud Run and trying to do the same is a totally different thing

That forced me to get much clearer about public API URLs, auth strings, service accounts, secrets, regions, and work pool defaults

Another challenge was the edge layer itself, DNS, Nginx, HTTPS, firewall rules, Basic Auth None of those were impossible, but they only really click once you go through them for real

The deploy flow was another good one Publishing deployments alone is not enough if the runtime image was not rebuilt first Sounds simple, but that is exactly the kind of thing that can make you think the deploy worked while the runtime is still using old code

So yeah, there were a few bumps, but honestly those were the exact kind of things I wanted to understand better

---

## Current status

At this point, the platform can already

- run a self hosted Prefect control plane
- expose the UI through a real domain with HTTPS
- keep dev and prod separated through workers and work pools
- build and push runtime images automatically
- publish deployments automatically
- execute real flows in Cloud Run Jobs
- send run status back to Prefect
- use runtime service accounts and secrets correctly
- complete end to end runs in both dev and prod

So the base is there now

This is not just a draft architecture anymore, it is actually working

---

## What comes next

Now that the orchestration foundation is working, the focus shifts more toward the actual platform and pipelines

The most natural next steps are

- add more real flows
- create reusable helpers for GCS, BigQuery, APIs, and other common pieces
- add schedules
- improve visibility and monitoring a bit
- harden a few remaining infra details
- keep documenting the platform as it evolves

That is probably the part I am most excited about now, because the project can finally move from “platform setup” into “real platform usage”
