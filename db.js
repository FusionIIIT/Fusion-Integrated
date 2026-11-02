const { Sequelize } = require('sequelize');

const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: ':memory:',
  logging: false,
  define: {
    timestamps: true,
    underscored: true,
  },
});

async function initializeDatabase() {
  await sequelize.authenticate();
  await sequelize.sync({ force: false, alter: false });
  return sequelize;
}

module.exports = {
  sequelize,
  initializeDatabase,
};
