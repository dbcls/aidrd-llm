FROM --platform=linux/amd64 node:19-bullseye-slim

WORKDIR /app
COPY --chown=node:node ./package.json ./

RUN yarn install

EXPOSE 3000

CMD ["yarn","start"]
