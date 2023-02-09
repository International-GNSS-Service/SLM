from slm.models import SingletonModel
from ckeditor_uploader.fields import RichTextUploadingField


class Help(SingletonModel):
    content = RichTextUploadingField(
        blank=True,
        null=False,
        default=''
    )
    class Meta:
        verbose_name = 'Page Content: Help'
        verbose_name_plural = "Page Content: Help"

    def __str__(self):
        return f'Help Content'