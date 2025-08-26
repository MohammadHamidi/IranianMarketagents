FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the React app
ARG REACT_APP_API_URL
ARG REACT_APP_ENVIRONMENT
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_ENVIRONMENT=$REACT_APP_ENVIRONMENT

RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
