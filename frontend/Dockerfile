FROM node:20-alpine
WORKDIR /app
# Copy the lockfile too and install from it. `npm install` with package.json
# alone ignored package-lock.json entirely, so the container could resolve
# different transitive versions than any developer's machine -- the classic
# "works locally, breaks in the demo container" failure.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
