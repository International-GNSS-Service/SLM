'''
Handles forms for site log sections, user
management.

NOTES:
This file was custom written for this particular
application.  User forms deal with registration
in regards to overriding default user model with 
a new custom user model.

There is a form for each sitelog field.  Further
improvements may include adding acceptable
answers for each field when necessary, making certain
fields required vs. preferred, fixing date input capabilities.

More info on forms:
https://docs.djangoproject.com/en/3.2/topics/forms/

More info on field types:
https://docs.djangoproject.com/en/3.2/ref/models/fields/
'''

from django import forms
from django.forms.fields import *
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField

User = get_user_model()  # accessesing custom User model

class RegisterForm(forms.ModelForm):
    # Default user registration form.

    password = forms.CharField(widget=forms.PasswordInput)
    password_2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email']

    def clean_email(self):
        '''
        Verify email is available.
        '''
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if qs.exists():
            raise forms.ValidationError("email is taken")
        return email

    def clean(self):
        # Verifying that both passwords match.
        
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_2 = cleaned_data.get("password_2")
        if password is not None and password != password_2:
            self.add_error("password_2", "Your passwords must match")
        return cleaned_data


class UserAdminCreationForm(forms.ModelForm):
    # Creates new users with all the required
    # fields. Requires repeated password.

    password = forms.CharField(widget=forms.PasswordInput)
    password_2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email']

    def clean(self):
        # Verify both passwords match.
        
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_2 = cleaned_data.get("password_2")
        if password is not None and password != password_2:
            self.add_error("password_2", "Your passwords must match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserAdminChangeForm(forms.ModelForm):
    """
    Updates users. Replaces password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ['email', 'password', 'is_active', 'is_superuser']

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]
        

# FileUpload form was started for upload feature.  Never
# finished
# See https://docs.djangoproject.com/en/3.2/topics/http/file-uploads/
class FileUpload(forms.Form): 
    File = forms.FileField()

class SiteForm_0(forms.Form):
    Prepared_By = forms.CharField(label="Prepared By", max_length=50)
    # Calendar selection?
    Date_Prepared = forms.DateField(label="Date Prepared", widget=forms.DateInput(attrs={'type':'date', 'min': '2020-01-01', 'max': 'date.today'}))
    Report_Type = forms.CharField(label="Report Type", max_length=50)
    # Give choices? 
    Previous_Log = forms.CharField(label="Previous Log", max_length=50)
    Mod_Sections = forms.CharField(label="Modified Sections", max_length=3000)

class Overview_1a(forms.Form):
    Site_Name = forms.CharField(label="Site Name", max_length=50)
    Site_Long_Name = forms.CharField(label="Site Long Name", max_length=50)
    Monument_Inscrip = forms.CharField(label="Monument Inscription", max_length=50)
    IERS_DOMES_Number = forms.CharField(label="IERS DOMES Number", max_length=50)
    CDP_Number = forms.CharField(label="CDP Number", max_length=50)
    Date_Installed_Overview = forms.DateField(label="Date Installed", widget=forms.DateInput(attrs={'type':'date'}))

class Monument_1b(forms.Form):
    Monument_Descrip = forms.CharField(label="Monument Description", max_length=50)
    Height_of_the_Monument = forms.CharField(label="Monument Height (m)", max_length=50)
    Monument_Found = forms.CharField(label="Monument Foundation", max_length=50)
    Found_Depth = forms.CharField(label="Foundation Depth (m)", max_length=50)
    Marker_Descrip = forms.CharField(label="Marker Description", max_length=50)

class GeologicCharacteristics_1c(forms.Form):
    Geologic_Char = forms.CharField(label="Geologic Characteristic", max_length=50)
    Bedrock_Type = forms.CharField(label="Bedrock Type", max_length=50)
    Bedrock_Condition = forms.CharField(label="Bedrock Condition", max_length=50)
    Fracture_Spacing = forms.CharField(label="Fracture Spacing", max_length=50)
    Fault_Zones_Nearby = forms.CharField(label="Fault Zones Nearby", max_length=50)
    Distance_Activity = forms.CharField(label="Distance/activity", max_length=3000, widget=forms.Textarea)
    Additional_Info_Geo = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)


class SiteLocation_2(forms.Form):
    City_Town = forms.CharField(label="City/town", max_length=50)
    State_Province = forms.CharField(label="State/province", max_length=50)
    Country = forms.CharField(label="Country/Region", max_length=50)
    # Give options
    Tectonic_Plate = forms.CharField(label="Tectonic Plate", max_length=50)
    X_coord = forms.CharField(label="X coordinate (m)", max_length=50)
    Y_coord = forms.CharField(label="Y coordinate (m)", max_length=50)
    Z_coord = forms.CharField(label="Z coordinate (m)", max_length=50)
    Latitude = forms.CharField(label="Latitude (N is +)", max_length=50)
    Longitude = forms.CharField(label="Longitude (E is +)", max_length=50)
    Elevation = forms.CharField(label="Elevation (m)", max_length=50)
    Additional_Info_Location = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class GNSSReceiver_3(forms.Form):
    Receiver_Type = forms.CharField(label="Receiver Type", max_length=50)
    Satellite_System = forms.CharField(label="Satellite System", max_length=50)
    Serial_Number_Receiver = forms.CharField(label="Serial Number", max_length=50)
    Firmware_Version = forms.CharField(label="Firmware Version", max_length=50)
    # options below
    Elev_Cutoff_Setting = forms.CharField(label="Elevation Cutoff Setting (deg)", max_length=50)
    Date_Installed_Receiver = forms.DateTimeField(label="Date Installed", widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    Date_Removed_Receiver = forms.DateTimeField(label="Date Removed", widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    Temperature_Stabiliz = forms.CharField(label="Temperature Stabiliz. (deg. C)", max_length=50)
    Additional_Info = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class GNSSAntennas_4(forms.Form):
    Antenna_Type = forms.CharField(label="Antenna Type", max_length=50)
    Serial_Number_Antenna = forms.CharField(label="Serial Number", max_length=50)
    Antenna_Ref_Point = forms.CharField(label="Antenna Reference Point", max_length=50)
    Marker_Up = forms.CharField(label="Marker -> ARP Up Ecc. (m)", max_length=50)
    Marker_North = forms.CharField(label="Marker -> ARP North Ecc. (m)", max_length=50)
    Marker_East = forms.CharField(label="Marker -> ARP East Ecc. (m)", max_length=50)
    Alignment_TrueN = forms.CharField(label="Alignment from True N", max_length=50)
    Antenna_Radome_Type = forms.CharField(label="Antenna Radome Type", max_length=50)
    Radome_Serial_Number = forms.CharField(label="Radome Serial Number", max_length=50)
    Antenna_Cable_Type = forms.CharField(label="Antenna Cable Type", max_length=50)
    Antenna_Cable_Length = forms.CharField(label="Antenna Cable Length", max_length=50)
    Date_Installed = forms.DateTimeField(label="Date Installed", widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    Date_Removed = forms.DateTimeField(label="Date Removed", widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    Additional_Info = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class SurveyedLocalTies_5(forms.Form):
    Tied_Marker_Name = forms.CharField(label="Tied Marker Name", max_length=50)
    Tied_Marker_Usage = forms.CharField(label="Tied Marker Usage", max_length=50)
    Tied_Marker_CDP_Number = forms.CharField(label="Tied Marker CDP Number", max_length=50)
    Tied_Marker_DOMES_Number = forms.CharField(label="Tied Marker DOMES Number", max_length=50)
    dx = forms.CharField(label="dx (m)", max_length=50)
    dy = forms.CharField(label="dy (m)", max_length=50)
    dz = forms.CharField(label="dz (m)", max_length=50)
    Accuracy_Survey = forms.CharField(label="Accuracy (mm)", max_length=50)
    Survey_Method = forms.CharField(label="Survey Method", max_length=50)
    Date_Measured = forms.DateTimeField(label="Date Measured", widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    Additional_Info_Survey = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class FrequencyStandard_6(forms.Form):
    Standard_Type = forms.CharField(label="Standard Type", max_length=50)
    Input_Frequency = forms.CharField(label="Input Frequency (MHz)", max_length=50)
    Eff_Start_Date_Freq = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Freq = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Notes_Freq = forms.CharField(label="Notes", max_length=3000, widget=forms.Textarea)

class CollocationInformation_7(forms.Form):
    Instrum_Type = forms.CharField(label="Instrumentation Type", max_length=50)
    Status = forms.CharField(label="Status", max_length=50)
    Eff_Start_Date_Collocation = forms.CharField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Collocation = forms.CharField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Notes_Collocation = forms.CharField(label="Notes", max_length=3000, widget=forms.Textarea)

class HumiditySensor_8_1(forms.Form):
    Humidity_Sensor_Model = forms.CharField(label="Humidity Sensor Model", max_length=50)
    Manufacturer_Humid = forms.CharField(label="Manufacturer", max_length=50)
    Serial_Number_Humid = forms.CharField(label="Serial Number", max_length=50)
    Data_Sampling_Interval_Humid = forms.CharField(label="Data Sampling Interval (sec)", max_length=50)
    Accuracy_Humid = forms.CharField(label="Accuracy (percentage rel h)", max_length=50)
    Aspiration_Humid = forms.CharField(label="Aspiration", max_length=50)
    Height_Diff_to_Ant_Humid = forms.CharField(label="Height Diff to Ant (m)", max_length=50)
    Calibration_Date_Humid = forms.DateField(label="Calibration Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_Start_Date_Humid = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Humid = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Notes_Humid = forms.CharField(label="Notes", max_length=3000, widget=forms.Textarea)

class PressureSensor_8_2(forms.Form):
    Pressure_Sensor_Model = forms.CharField(label="Pressure Sensor Model", max_length=50)
    Manufacturer_Pressure = forms.CharField(label="Manufacturer", max_length=50)
    Serial_Number_Pressure = forms.CharField(label="Serial Number", max_length=50)
    Data_Sampling_Interval_Pressure = forms.CharField(label="Data Sampling Interval (sec)", max_length=50)
    Accuracy_Pressure = forms.CharField(label="Accuracy (hPa)", max_length=50)
    Height_Diff_to_Ant_Pressure = forms.CharField(label="Height Diff to Ant (m)", max_length=50)
    Calibration_Date_Pressure = forms.DateField(label="Calibration Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_Start_Date_Pressure = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Pressure = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Notes_Pressure = forms.CharField(label="Notes", max_length=3000, widget=forms.Textarea)

class TemperatureSensor_8_3(forms.Form):
    Temp_Sensor_Model = forms.CharField(label="Temperature Sensor Model", max_length=50)
    Manufacturer_Temp = forms.CharField(label="Manufacturer", max_length=50)
    Serial_Number_Temp = forms.CharField(label="Serial Number", max_length=50)
    Data_Sampling_Interval_Temp = forms.CharField(label="Data Sampling Interval (sec)", max_length=50)
    Accuracy_Temp = forms.CharField(label="Accuracy (deg C)", max_length=50)
    Aspiration_Temp = forms.CharField(label="Aspiration", max_length=50)
    Height_Diff_to_Ant_Temp = forms.CharField(label="Height Diff to Ant (m)", max_length=50)
    Calibration_Date_Temp = forms.DateField(label="Calibration Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_Start_Date_Temp = forms.DateField(label="Calibration Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Temp = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Notes_Temp = forms.CharField(label="Notes", max_length=3000, widget=forms.Textarea)

class WaterVaporRadiometer_8_4(forms.Form):
    Water_Vapor_Radiometer = forms.CharField(label="Water Vapor Radiometer", max_length=50)
    Manufacturer_Water = forms.CharField(label="Manufacturer", max_length=50)
    Serial_Number_Water = forms.CharField(label="Serial Number", max_length=50)
    Distance_to_Antenna_Water = forms.CharField(label="Distance to Antenna (m)", max_length=50)
    Height_Diff_to_Ant_Water = forms.CharField(label="Height Diff to Ant (m)", max_length=50)
    Calibration_Date_Water = forms.DateField(label="Calibration Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_Start_Date_Water = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Water = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Notes_Water = forms.CharField(label="Notes", max_length=3000, widget=forms.Textarea)

class OtherInstrumentation_8_5(forms.Form):
    Other_Instrum = forms.CharField(label="Other Instrumentation", max_length=3000, widget=forms.Textarea)

class RadioInterference_9_1(forms.Form):
    Radio_Interferences = forms.CharField(label="Radio Interferences", max_length=50)
    Observed_Degrad = forms.CharField(label="Observed Degradation", max_length=50)
    Eff_Start_Date_Radio = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_Dates_Radio = forms.DateField(label="Effective Dates", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Radio = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Additional_Info_Radio = forms.CharField(label="Additional Info", max_length=3000, widget=forms.Textarea)

class Multipath_9_2(forms.Form):
    Multipath_Sources = forms.CharField(label="Multipath Sources", max_length=50)
    Eff_Start_Date_Multi = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Multi = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Additional_Info_Multi = forms.CharField(label="Additional Info", max_length=3000, widget=forms.Textarea)

class Signal_9_3(forms.Form):
    Signal_Obstructions = forms.CharField(label="Signal Obstructions", max_length=50)
    Eff_Start_Date_Signal = forms.DateField(label="Effective Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    Eff_End_Date_Signal = forms.DateField(label="Effective End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Additional_Info_Signal = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class LocalEpisodicEffects_10(forms.Form):
    Start_Date_Episodic = forms.DateField(label="Start Date", widget=forms.DateInput(attrs={'type':'date'}))
    End_Date_Episodic = forms.DateField(label="End Date", widget=forms.DateInput(attrs={'type':'date'}))
    Event = forms.CharField(label="Event", max_length=3000, widget=forms.Textarea)

class OnSitePointofContact_11(forms.Form):
    Agency_PoC = forms.CharField(label="Agency", max_length=50)
    Preferred_Abbrev = forms.CharField(label="Preferred Abbreviation", max_length=50)
    Mailing_Address_PoC = forms.CharField(label="Mailing Address", max_length=1000, widget=forms.Textarea)
    Contact_Name_PoC = forms.CharField(label="Contact Name", max_length=50)
    Phone_Primary_PoC = forms.CharField(label="Phone (primary)", max_length=50)
    Phone_Secondary_PoC = forms.CharField(label="Phone (seconday)", max_length=50)
    Fax_PoC = forms.CharField(label="Fax", max_length=50)
    Email_PoC = forms.EmailField(label="E-mail", max_length=50)
    Sec_Contact_Name_PoC = forms.CharField(label="Secondary Contact Name", max_length=50)
    Sec_Telephone_Prim_PoC = forms.CharField(label="Secondary Phone (primary)", max_length=50)
    Sec_Telephone_Sec_PoC = forms.CharField(label="Secondary Phone (secondary)", max_length=50)
    Sec_Fax = forms.CharField(label="Secondary Fax", max_length=50)
    Sec_Email = forms.CharField(label="Secondary E-mail", max_length=50)
    Additional_Info_PoC = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class ResponsibleAgencyInfo_12(forms.Form):
    Agency_Resp = forms.CharField(label="Agency", max_length=50)
    Preferred_Abbrev_Resp = forms.CharField(label="Preferred Abbreviation", max_length=50)
    Mailing_Address_Resp = forms.CharField(label="Mailing Address", max_length=1000, widget=forms.Textarea)
    Contact_Name_Resp = forms.CharField(label="Contact Name", max_length=50)
    Phone_Primary_Resp = forms.CharField(label="Phone (primary)", max_length=50)
    Phone_Secondar_Resp = forms.CharField(label="Phone (secondary)", max_length=50)
    Fax_Resp = forms.CharField(label="Fax", max_length=50)
    Email_Resp = forms.EmailField(label="E-mail", max_length=50)
    Sec_Contact_Name_Resp = forms.CharField(label="Secondary Contact Name", max_length=50)
    Sec_Telephone_Prim_Resp = forms.CharField(label="Secondary Phone (primary)", max_length=50)
    Sec_Telephone_Sec_Resp = forms.CharField(label="Secondary Phone (secondary)", max_length=50)
    Sec_Fax_Resp = forms.CharField(label="Secondary Fax", max_length=50)
    Sec_Email_Resp = forms.CharField(label="Secondary E-mail", max_length=50)
    Additional_Info_Resp = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class Details_13_0(forms.Form):
    Primary_Data_Center = forms.CharField(label="Primary Data Center", max_length=50)
    Secondary_Data_Center = forms.CharField(label="Secondary Data Center", max_length=50)
    URL_for_More_Info = forms.CharField(label="URL for More Information", max_length=50)
    Site_Map_URL = forms.CharField(label="Site Map URL", max_length=50)
    Site_Diagram = forms.CharField(label="Site Diagram", max_length=50)
    Horizon_Mask_URL = forms.CharField(label="Horizon Mask URL", max_length=50)
    Monument_Description_URL = forms.CharField(label="Monument Description URL", max_length=50)
    Site_Pictures_URL = forms.CharField(label="Site Pictures URL", max_length=50)
    Additional_Info_Details = forms.CharField(label="Additional Information", max_length=3000, widget=forms.Textarea)

class AntennaGraphics_13_1(forms.Form):
    Antenna_Graphics = forms.CharField(label="Antenna Graphics", max_length=3000, widget=forms.Textarea)
