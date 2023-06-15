# ftl_extractor
recovery Flash Translation Layer vol from flash dump

flash or SD Card may have an FTL(Flash Translation Layer) between the upper filesystem(eg. fat) and flash. So if we use a flash programmer to dump data, maybe we can't analyze the filesystem directly because we need to reform all the data to its logical address.

## Usage

```sh
# need python3 and construct
# pip install construct
python ftl_extractor.py input_dump output.bin
```

## References

* `intel AP-684 Understanding the Flash Translation Layer (FTL) Specification`
* `ftllite.c` in VxWorks 6.9 and `ftllite.o` in VxWorks 5.5