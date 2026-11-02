const PmsPatentApplication = require('./pms_patent_applications');
const PmsPatentCategory = require('./pms_patent_categories');
const PmsPatentInventor = require('./pms_patent_inventors');
const PmsPatentReview = require('./pms_patent_reviews');

PmsPatentApplication.hasMany(PmsPatentInventor, {
  foreignKey: 'applicationId',
  as: 'inventors',
  onDelete: 'CASCADE',
});
PmsPatentInventor.belongsTo(PmsPatentApplication, { foreignKey: 'applicationId', as: 'application' });

PmsPatentApplication.hasMany(PmsPatentReview, {
  foreignKey: 'applicationId',
  as: 'reviews',
  onDelete: 'CASCADE',
});
PmsPatentReview.belongsTo(PmsPatentApplication, { foreignKey: 'applicationId', as: 'application' });

PmsPatentCategory.hasMany(PmsPatentApplication, { foreignKey: 'categoryId', as: 'applications' });
PmsPatentApplication.belongsTo(PmsPatentCategory, { foreignKey: 'categoryId', as: 'category' });

module.exports = {
  PmsPatentApplication,
  PmsPatentCategory,
  PmsPatentInventor,
  PmsPatentReview,
};
