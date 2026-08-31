FROM node:20-alpine

WORKDIR /usr/src/app

COPY app/package*.json ./
RUN npm ci

COPY app/ ./

EXPOSE 4200

CMD ["npm", "run", "start:docker"]
