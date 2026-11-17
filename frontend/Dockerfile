# Dev server:  docker build --target dev -t coach-frontend-dev .
# Production:  docker build --build-arg VITE_API_URL=https://api.example.com -t coach-frontend .
FROM node:20-slim AS dev
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM dev AS build
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
RUN printf 'server {\n listen 80;\n root /usr/share/nginx/html;\n location / { try_files $uri /index.html; }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
