from django.db import models
class NetworkInfo(models.Model):
    networkid = models.AutoField(db_column='NetworkID', primary_key=True)  # Field name made lowercase.
    networkname = models.CharField(db_column='NetworkName', max_length=100, blank=True, null=True)  # Field name made lowercase.
    webpagedefaultshow = models.IntegerField(db_column='WebPageDefaultShow')  # Field name made lowercase.
    displayorder = models.IntegerField(db_column='DisplayOrder')  # Field name made lowercase.
    mappin = models.CharField(db_column='MapPin', max_length=50, blank=True, null=True)  # Field name made lowercase.

    def __str__(self):
        return self.networkname

    class Meta:
        managed = False
        db_table = 'Network'


class Networksites(models.Model):
    networkid = models.IntegerField(db_column='NetworkID', blank=True, null=True)  # Field name made lowercase.
    fourid = models.CharField(db_column='FourID', max_length=40, db_collation='utf8_general_ci')  # Field name made lowercase.
    # id = models.IntegerField(db_column='id', blank=True, null=True)
    fk = models.ForeignKey(NetworkInfo, on_delete=models.CASCADE)
        
    class Meta:
        managed = False
        db_table = 'NetworkSites'


class Networkscategory(models.Model):
    category = models.CharField(db_column='Category', max_length=50, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'NetworksCategory'